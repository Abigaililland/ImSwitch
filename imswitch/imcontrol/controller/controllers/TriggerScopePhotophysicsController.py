import os
import configparser
from ast import literal_eval
from ..basecontrollers import ImConWidgetController
import numpy as np
import traceback
import functools
from imswitch.imcommon.model import APIExport, dirtools
from imswitch.imcontrol.view import guitools
from imswitch.imcommon.view.guitools import colorutils

class TriggerScopePhotophysicsController(ImConWidgetController):
    """ Linked to TriggerScopeRasterWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settingAttr = False
        self.settingParameters = False

        self._scanParameterDict = {}
        self._deviceParameterDict = {}

        self.isRunning = False
        self.doingNonFinalPartOfSequence = False

        self.scanDir = os.path.join(dirtools.UserFileDirs.Root, 'imcontrol_scans')
        if not os.path.exists(self.scanDir):
            os.makedirs(self.scanDir)

        self.updateScanParDict()

        self.positioners = {
            pName: pManager for pName, pManager in self._setupInfo.positioners.items()
            if pManager.forScanning
        }
        self.TTLDevices = self._setupInfo.getTTLDevices()
        #Add TTL devices to combobox
        self._widget.onLaserEdit.addItems(self.TTLDevices.keys())
        self._widget.offLaserEdit.addItems(self.TTLDevices.keys())

        self._widget.cycleScanDeviceEdit.addItems(self.positioners.keys())

        self.plotSignalGraph()

        # Connect NidaqManager signals
        self._master.triggerScopeManager.sigScanStarted.connect(
            lambda: self.emitScanSignal(self._commChannel.sigScanStarted)
        )
        self._master.triggerScopeManager.sigScanDone.connect(self.scanDone)

        # Connect CommunicationChannel signals
        self._commChannel.sigRunScan.connect(self.runScanExternal)
        self._commChannel.sigAbortScan.connect(self.abortScan)

        # Connect ScanWidget signals
        self._widget.sigSaveScanClicked.connect(self.saveScan)
        self._widget.sigLoadScanClicked.connect(self.loadScan)
        self._widget.sigRunScanClicked.connect(self.runScan)
        self._widget.sigParameterChanged.connect(self.updateScanParDict)
        self._widget.sigParameterChanged.connect(self.plotSignalGraph)

    def getNumScanPositions(self):
        """ Returns the number of scan positions for the configured scan. """
        _, positions, _ = self._master.triggerScopeManager.getScanSignalsDict(self._analogParameterDict)
        numPositions = functools.reduce(lambda x, y: x * y, positions)
        return numPositions

    def saveScan(self):
        fileName = guitools.askForFilePath(self._widget, 'Save scan', self.scanDir, isSaving=True)
        if not fileName:
            return

        self.saveScanParamsToFile(fileName)

    # @APIExport(runOnUIThread=True)
    def saveScanParamsToFile(self, filePath: str) -> None:
        """ Saves the set scanning parameters to the specified file. """
        self.getParameters()
        config = configparser.ConfigParser()
        config.optionxform = str

        config['scanParameterDict'] = self._scanParameterDict
        config['deviceParameterDict'] = self._deviceParameterDict

        with open(filePath, 'w') as configfile:
            config.write(configfile)

    def loadScan(self):
        fileName = guitools.askForFilePath(self._widget, 'Load scan', self.scanDir)
        if not fileName:
            return

        self.loadScanParamsFromFile(fileName)

    # @APIExport(runOnUIThread=True)
    def loadScanParamsFromFile(self, filePath: str) -> None:
        """ Loads scanning parameters from the specified file. """

        config = configparser.ConfigParser()
        config.optionxform = str

        config.read(filePath)

        for key in self._scanParameterDict:
            self._scanParameterDict[key] = literal_eval(
                config._sections['scanParameterDict'][key]
            )
        for key in self._deviceParameterDict:
            self._deviceParameterDict[key] = config._sections['deviceParameterDict'][key]

        self.setParameters()
        self.setAllSharedAttr()

    def setParameters(self):
        """Set parameter fields in widget according to parameter values in parameter dictionaries"""
        self.settingParameters = True
        try:
            #Set scan parameters
            self._widget.setTimeLapsePoints(self._scanParameterDict['timeLapsePoints'])
            self._widget.setTimeLapseDelayS(self._scanParameterDict['timeLapseDelayS'])
            self._widget.setOnTimeMs(self._scanParameterDict['onTimeMs'])
            self._widget.setDelayAfterOnTimeMs(self._scanParameterDict['delayAfterOnTimeMs'])
            self._widget.setOffTimeMs(self._scanParameterDict['offTimeMs'])
            self._widget.setDelayAfterOffTimeMs(self._scanParameterDict['delayAfterOffTimeMs'])
            #Set devices
            self._widget.setOnLaser(self._deviceParameterDict['onLaser'])
            self._widget.setOffLaser(self._deviceParameterDict['offLaser'])
            self._widget.setCycleScanDevice(self._deviceParameterDict['cycleScanDevice'])

        finally:
            self.settingParameters = False
            self.plotSignalGraph()


    def getTriggerscopeParameters(self):
        self.getParameters()
        deviceParameterDict = self._deviceParameterDict

        scanParameterDict = {}
        scanParameterDict['onPulseTimeUs'] = int(self._scanParameterDict['onTimeMs'] * 1000)
        scanParameterDict['offPulseTimeUs'] = int(self._scanParameterDict['offTimeMs'] * 1000)
        scanParameterDict['timeLapsePoints'] = int(self._scanParameterDict['timeLapsePoints'])
        scanParameterDict['timeLapseDelayUs'] = int(self._scanParameterDict['timeLapseDelayS'] * 1000000)
        scanParameterDict['delayAfterOnUs'] = int(self._scanParameterDict['delayAfterOnTimeMs'] * 1000)
        scanParameterDict['delayAfterOffUs'] = int(self._scanParameterDict['delayAfterOffTimeMs'] * 1000)

        pLSRParameterDict = {'deviceParameters': deviceParameterDict, 'scanParameters': scanParameterDict}

        return pLSRParameterDict

    def runScanExternal(self, recalculateSignals, isNonFinalPartOfSequence):
        self._widget.setRepeatEnabled(False)
        self.runScanAdvanced(recalculateSignals=recalculateSignals,
                             isNonFinalPartOfSequence=isNonFinalPartOfSequence,
                             sigScanStartingEmitted=True)

    def runScanAdvanced(self, *, recalculateSignals=True, isNonFinalPartOfSequence=False,
                        sigScanStartingEmitted):
        """ Runs a scan with the set scanning parameters. """
        #Temp safety fix
        # if self._widget.timeLapsePointsEdit.value() * self._widget.timeLapseDelayEdit.value() > 60:
        if self._widget.autoStartRec:
            self._commChannel.sigStartRecording.emit()
        try:
            self._widget.setScanButtonChecked(True)
            self.isRunning = True

            self.doingNonFinalPartOfSequence = isNonFinalPartOfSequence

            if not sigScanStartingEmitted:
                self.emitScanSignal(self._commChannel.sigScanStarting)
            triggerscopeParameters = self.getTriggerscopeParameters()
            self._master.triggerScopeManager.runScan(triggerscopeParameters, type='MifobioScan')

        except Exception:
            self._logger.error(traceback.format_exc())
            self.isRunning = False

    def abortScan(self):
        self.doingNonFinalPartOfSequence = False  # So that sigScanEnded is emitted
        if not self.isRunning:
            self.scanFailed()


    def scanDone(self):
        self._logger.debug('Scan done')
        self.isRunning = False

        self.emitScanSignal(self._commChannel.sigScanDone)
        if not self.doingNonFinalPartOfSequence:
            self._widget.setScanButtonChecked(False)
            self.emitScanSignal(self._commChannel.sigScanEnded)

        if self._widget.autoStopRec:
            self._commChannel.sigStopRecording.emit()

    def scanFailed(self):
        self._logger.error('Scan failed')
        self.isRunning = False
        self.doingNonFinalPartOfSequence = False
        self._widget.setScanButtonChecked(False)
        self.emitScanSignal(self._commChannel.sigScanEnded)

    def getParameters(self):
        """Get parameters from widget field to controller dict"""
        if self.settingParameters:
            return
        #Get scan parameters
        self._scanParameterDict['timeLapsePoints'] = self._widget.getTimeLapsePoints()
        self._scanParameterDict['timeLapseDelayS'] = self._widget.getTimeLapseDelayS()
        self._scanParameterDict['onTimeMs'] = self._widget.getOnTimeMs()
        self._scanParameterDict['delayAfterOnTimeMs'] = self._widget.getDelayAfterOnTimeMs()
        self._scanParameterDict['offTimeMs'] = self._widget.getOffTimeMs()
        self._scanParameterDict['delayAfterOffTimeMs'] = self._widget.getDelayAfterOffTimeMs()
        #Get device parameters
        self._deviceParameterDict['onLaser'] = self._widget.getOnLaser()
        self._deviceParameterDict['offLaser'] = self._widget.getOffLaser()
        self._deviceParameterDict['cycleScanDevice'] = self._widget.getCycleScanDevice()

    def plotSignalGraph(self):

        OnTime = self._widget.getOnTimeMs()
        DelayAfterOnTime = self._widget.getDelayAfterOnTimeMs()
        OffTime = self._widget.getOffTimeMs()
        dwellTime = float(OnTime + DelayAfterOnTime + OffTime+10)
        graphSamples = 10000

        areas = []
        signals = []
        colors = []
        for i in range(3):

            x = np.linspace(0, dwellTime, graphSamples)
            signal = np.zeros(graphSamples)
            try:
                # start = float(self._widget.pxParameters['sta' + deviceName].text())
                # end = float(self._widget.pxParameters['end' + deviceName].text())
                if i == 0:
                    signal[x > 0] = 1
                    #signal[x < OnTime] = 1
                    signal[x > OnTime] = 0
                    color_test = '#8200c8'
                elif i ==1:
                    signal[x > OnTime] = 0
                    signal[x < OnTime+DelayAfterOnTime] = 0
                    color_test = '#000000'
                elif i ==2:
                    signal[(x > OnTime+DelayAfterOnTime)] = 1
                    signal[x> OnTime+DelayAfterOnTime+OffTime] = 0
                    color_test = '#00f7ff'

            except ValueError:
                pass
            areas.append(x)
            signals.append(signal)
            # colors.append(
            #     colorutils.wavelengthToHex(
            #         self._setupInfo.lasers[deviceName].wavelength
            #     ) if isLaser else '#ffffff'
            # )
            colors.append(color_test)
        # for deviceName in self.TTLDevices.keys():
        #     isLaser = deviceName in self._setupInfo.lasers
        #     x = np.linspace(0, dwellTime, graphSamples)
        #     signal = np.zeros(graphSamples)
        #     try:
        #         # start = float(self._widget.pxParameters['sta' + deviceName].text())
        #         # end = float(self._widget.pxParameters['end' + deviceName].text())
        #         signal[x < OnTime] = 1
        #         signal[(x > OnTime) & (x < OnTime+DelayAfterOnTime)] = 0
        #         signal[(x > OnTime+DelayAfterOnTime) & (x < OnTime+DelayAfterOnTime+OffTime)] = 1
        #
        #     except ValueError:
        #         pass
        #     areas.append(x)
        #     signals.append(signal)
        #     # colors.append(
        #     #     colorutils.wavelengthToHex(
        #     #         self._setupInfo.lasers[deviceName].wavelength
        #     #     ) if isLaser else '#ffffff'
        #     # )
        #     colors.append('#00ffea')
        self._widget.plotSignalGraph(areas, signals, colors)
    def emitScanSignal(self, signal, *args):
        signal.emit(*args)

    # @APIExport(runOnUIThread=True)
    def runScan(self) -> None:
        """ Runs a scan with the set scanning parameters. """
        self.runScanAdvanced(sigScanStartingEmitted=False)

    def attrChanged(self, key, value):
        if self.settingAttr or len(key) != 2:
            return

        if key[0] == _attrCategoryScan:
            self._scanParameterDict[key[1]] = value
            self.setParameters()
        elif key[0] == _attrCategoryDevices:
            self._scanParameterDict[key[1]] = value
            self.setParameters()

    def setSharedAttr(self, category, attr, value):
        self.settingAttr = True
        try:
            self._commChannel.sharedAttrs[(category, attr)] = value
        finally:
            self.settingAttr = False

    def updateScanParDict(self):

        self.getParameters()
        self.setAllSharedAttr()

    def setAllSharedAttr(self):
        for key, value in self._scanParameterDict.items():
            self.setSharedAttr(_attrCategoryScan, key, value)

    def closeEvent(self):
        pass

_attrCategoryScan = 'MS-RESOLFT_Scan'
_attrCategoryDevices = 'MS-RESOLFT_Dev'
# Copyright (C) 2020-2021 ImSwitch developers
# This file is part of ImSwitch.
#
# ImSwitch is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ImSwitch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.