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

class LightSheetMulticolorController(ImConWidgetController):
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
        self._widget.Laser1Edit.addItems(self.TTLDevices.keys())
        self._widget.Laser2Edit.addItems(self.TTLDevices.keys())
        self._widget.Laser3Edit.addItems(self.TTLDevices.keys())
        self._widget.Laser4Edit.addItems(self.TTLDevices.keys())
        self._widget.Laser5Edit.addItems(self.TTLDevices.keys())
        self._widget.CameraTTLEdit.addItems(self.TTLDevices.keys())
        # self._widget.roLaserEdit.addItems(self.TTLDevices.keys())

        self._widget.roScanDeviceEdit.addItems(self.positioners.keys())
        self._widget.MulticolorScanDeviceEdit.addItems(self.positioners.keys())

        self._widget.cycleScanDeviceEdit.addItems(self.positioners.keys())

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
            self._widget.setLaser1OnMs(self._scanParameterDict['Laser1OnMs'])
            self._widget.setDelayAfterLaser1Ms(self._scanParameterDict['DelayAfterLaser1Ms'])
            self._widget.setLaser2OnMs(self._scanParameterDict['Laser2OnMs'])
            self._widget.setDelayAfterLaser2Ms(self._scanParameterDict['DelayAfterLaser2Ms'])
            self._widget.setLaser3OnMs(self._scanParameterDict['Laser3OnMs'])
            self._widget.setDelayAfterLaser3Ms(self._scanParameterDict['DelayAfterLaser3Ms'])
            self._widget.setLaser4OnMs(self._scanParameterDict['Laser4OnMs'])
            self._widget.setDelayAfterLaser4Ms(self._scanParameterDict['DelayAfterLaser4Ms'])
            self._widget.setLaser5OnMs(self._scanParameterDict['Laser5OnMs'])
            self._widget.setDelayAfterLaser5Ms(self._scanParameterDict['DelayAfterLaser5Ms'])
            self._widget.setRoRestingPosUm(self._scanParameterDict['roRestingPosUm'])
            self._widget.setRoStartPosUm(self._scanParameterDict['roStartPosUm'])
            self._widget.setRoStepSizeUm(self._scanParameterDict['roStepSizeUm'])
            self._widget.setRoSteps(self._scanParameterDict['roSteps'])
            self._widget.setCycleStartPosUm(self._scanParameterDict['cycleStartPosUm'])
            self._widget.setCycleStepSizeUm(self._scanParameterDict['cycleStepSizeUm'])
            self._widget.setCycleSteps(self._scanParameterDict['cycleSteps'])
            self._widget.setMulticolorScanFirstUm(self._scanParameterDict['MulticolorScanFirstUm'])
            self._widget.setMulticolorScanSecondUm(self._scanParameterDict['MulticolorScanSecondUm'])

            #Set devices

            self._widget.setLaser1(self._deviceParameterDict['Laser1'])
            self._widget.setLaser2(self._deviceParameterDict['Laser2'])
            self._widget.setLaser3(self._deviceParameterDict['Laser3'])
            self._widget.setLaser4(self._deviceParameterDict['Laser4'])
            self._widget.setLaser5(self._deviceParameterDict['Laser5'])
            self._widget.setCameraTTL(self._deviceParameterDict['CameraTTL'])
            self._widget.setRoScanDevice(self._deviceParameterDict['roScanDevice'])
            self._widget.setMulticolorScanDevice(self._deviceParameterDict['MulticolorScanDevice'])
            self._widget.setCycleScanDevice(self._deviceParameterDict['cycleScanDevice'])



        finally:
            self.settingParameters = False


    def getTriggerscopeParameters(self):
        self.getParameters()
        deviceParameterDict = self._deviceParameterDict

        scanParameterDict = {}
        roConvFactor = self.positioners[deviceParameterDict['roScanDevice']].managerProperties['conversionFactor']
        cycleConvFactor = self.positioners[deviceParameterDict['cycleScanDevice']].managerProperties['conversionFactor']
        scanParameterDict['Laser1OnUs'] = int(self._scanParameterDict['Laser1OnMs'] * 1000)
        scanParameterDict['Laser2OnUs'] = int(self._scanParameterDict['Laser2OnMs'] * 1000)
        scanParameterDict['Laser3OnUs'] = int(self._scanParameterDict['Laser3OnMs'] * 1000)
        scanParameterDict['Laser4OnUs'] = int(self._scanParameterDict['Laser4OnMs'] * 1000)
        scanParameterDict['Laser5OnUs'] = int(self._scanParameterDict['Laser5OnMs'] * 1000)
        scanParameterDict['timeLapsePoints'] = int(self._scanParameterDict['timeLapsePoints'])
        scanParameterDict['timeLapseDelayUs'] = int(self._scanParameterDict['timeLapseDelayS'] * 1000000)
        scanParameterDict['DelayAfterLaser1Us'] = int(self._scanParameterDict['DelayAfterLaser1Ms'] * 1000)
        scanParameterDict['DelayAfterLaser2Us'] = int(self._scanParameterDict['DelayAfterLaser2Ms'] * 1000)
        scanParameterDict['roRestingV'] = self._scanParameterDict['roRestingPosUm'] / roConvFactor
        scanParameterDict['roStartV'] = self._scanParameterDict['roStartPosUm'] / roConvFactor
        scanParameterDict['roStepSizeV'] = self._scanParameterDict['roStepSizeUm'] / roConvFactor
        scanParameterDict['MulticolorScanFirstV'] = self._scanParameterDict['MulticolorScanFirstUm'] / roConvFactor
        scanParameterDict['MulticolorScanSecondV'] = self._scanParameterDict['MulticolorScanSecondUm'] / roConvFactor
        scanParameterDict['roSteps'] = int(self._scanParameterDict['roSteps'])
        scanParameterDict['cycleStartV'] = self._scanParameterDict['cycleStartPosUm'] / roConvFactor
        scanParameterDict['cycleStepSizeV'] = self._scanParameterDict['cycleStepSizeUm'] / roConvFactor
        scanParameterDict['cycleSteps'] = int(self._scanParameterDict['cycleSteps'])



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
            self._master.triggerScopeManager.runScan(triggerscopeParameters, type='MulticolorScan')

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
        self._scanParameterDict['Laser1OnMs'] = self._widget.getLaser1OnMs()
        self._scanParameterDict['DelayAfterLaser1Ms'] = self._widget.getDelayAfterLaser1Ms()
        self._scanParameterDict['Laser2OnMs'] = self._widget.getLaser2OnMs()
        self._scanParameterDict['DelayAfterLaser2Ms'] = self._widget.getDelayAfterLaser2Ms()
        self._scanParameterDict['Laser3OnMs'] = self._widget.getLaser3OnMs()
        self._scanParameterDict['DelayAfterLaser3Ms'] = self._widget.getDelayAfterLaser3Ms()
        self._scanParameterDict['Laser4OnMs'] = self._widget.getLaser4OnMs()
        self._scanParameterDict['DelayAfterLaser4Ms'] = self._widget.getDelayAfterLaser4Ms()
        self._scanParameterDict['Laser5OnMs'] = self._widget.getLaser5OnMs()
        self._scanParameterDict['DelayAfterLaser5Ms'] = self._widget.getDelayAfterLaser5Ms()

        self._scanParameterDict['roRestingPosUm'] = self._widget.getRoRestingPosUm()
        self._scanParameterDict['roStartPosUm'] = self._widget.getRoStartPosUm()
        self._scanParameterDict['roStepSizeUm'] = self._widget.getRoStepSizeUm()
        self._scanParameterDict['MulticolorScanFirstUm'] = self._widget.getMulticolorScanFirstUm()
        self._scanParameterDict['MulticolorScanSecondUm'] = self._widget.getMulticolorScanSecondUm()
        self._scanParameterDict['roSteps'] = self._widget.getRoSteps()
        self._scanParameterDict['cycleStartPosUm'] = self._widget.getCycleStartPosUm()
        self._scanParameterDict['cycleStepSizeUm'] = self._widget.getCycleStepSizeUm()
        self._scanParameterDict['cycleSteps'] = self._widget.getCycleSteps()


        #Get device parameters
        self._deviceParameterDict['Laser1'] = self._widget.getLaser1()
        self._deviceParameterDict['Laser2'] = self._widget.getLaser2()
        self._deviceParameterDict['Laser3'] = self._widget.getLaser3()
        self._deviceParameterDict['Laser4'] = self._widget.getLaser4()
        self._deviceParameterDict['Laser5'] = self._widget.getLaser5()
        self._deviceParameterDict['CameraTTL'] = self._widget.getCameraTTL()
        self._deviceParameterDict['roScanDevice'] = self._widget.getRoScanDevice()
        self._deviceParameterDict['MulticolorScanDevice'] = self._widget.getMulticolorScanDevice()

        self._deviceParameterDict['cycleScanDevice'] = self._widget.getCycleScanDevice()

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