import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget


class LightSheetMulticolorWidget(Widget):
    """ Widget containing scanner interface and beadscan reconstruction.
            This class uses the classes GraphFrame, MultipleScanWidget and IllumImageWidget"""

    sigSaveScanClicked = QtCore.Signal()
    sigLoadScanClicked = QtCore.Signal()
    sigRunScanClicked = QtCore.Signal()
    sigParameterChanged = QtCore.Signal()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setMinimumHeight(200)

        self.scanInLiveviewWar = QtWidgets.QMessageBox()
        self.scanInLiveviewWar.setInformativeText(
            "You need to be in liveview to scan")

        self.digModWarning = QtWidgets.QMessageBox()
        self.digModWarning.setInformativeText(
            "You need to be in digital laser modulation and external "
            "frame-trigger acquisition mode")
        self.scannerLabel = QtWidgets.QLabel('pLS-multicolor')
        self.scannerLabel.setStyleSheet('font-size: 14pt; font-weight: bold')

        self.saveScanBtn = guitools.BetterPushButton('Save Scan')
        self.loadScanBtn = guitools.BetterPushButton('Load Scan')


        autoStartRecLabel = QtWidgets.QLabel('Auto-start REC')
        autoStartRecLabel.setAlignment(QtCore.Qt.AlignRight)
        self.autoStartRec = QtWidgets.QCheckBox()
        autoStopRecLabel = QtWidgets.QLabel('Auto-stop REC')
        autoStopRecLabel.setAlignment(QtCore.Qt.AlignRight)
        self.autoStopRec = QtWidgets.QCheckBox()
        self.scanButton = guitools.BetterPushButton('Run Scan')

        self.scrollContainer = QtWidgets.QGridLayout()
        self.scrollContainer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.scrollContainer)

        self.grid = QtWidgets.QGridLayout()
        self.gridContainer = QtWidgets.QWidget()
        self.gridContainer.setLayout(self.grid)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scrollArea.setWidget(self.gridContainer)
        self.scrollArea.setWidgetResizable(True)
        self.scrollContainer.addWidget(self.scrollArea)
        self.gridContainer.installEventFilter(self)

        """Scan value parameters"""
        self.scanPar = {}

        timeLapsePointsLabel = QtWidgets.QLabel('Time lapse timepoints')
        self.timeLapsePointsEdit = guitools.BetterSpinBox(allowScrollChanges=False)
        self.timeLapsePointsEdit.editingFinished.connect(self.sigParameterChanged)

        timeLapseDelayLabel = QtWidgets.QLabel('Time lapse delay (sec)')
        self.timeLapseDelayEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.timeLapseDelayEdit.setMaximum(1000)
        self.timeLapseDelayEdit.editingFinished.connect(self.sigParameterChanged)

        Laser1OnLabel = QtWidgets.QLabel('Laser 1 on time (ms)')
        self.Laser1OnEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.Laser1OnEdit.editingFinished.connect(self.sigParameterChanged)

        DelayAfterLaser1Label = QtWidgets.QLabel('Delay after Laser 1 (ms)')
        self.DelayAfterLaser1Edit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.DelayAfterLaser1Edit.setMaximum(1000)
        self.DelayAfterLaser1Edit.editingFinished.connect(self.sigParameterChanged)

        Laser2OnLabel = QtWidgets.QLabel('Laser 2 on time (ms)')
        self.Laser2OnEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.Laser2OnEdit.editingFinished.connect(self.sigParameterChanged)

        DelayAfterLaser2Label = QtWidgets.QLabel('Delay after Laser 2 (ms)')
        self.DelayAfterLaser2Edit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.DelayAfterLaser2Edit.setMaximum(1000)
        self.DelayAfterLaser2Edit.editingFinished.connect(self.sigParameterChanged)

        Laser3OnLabel = QtWidgets.QLabel('Laser 3 on time (ms)')
        self.Laser3OnEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.Laser3OnEdit.editingFinished.connect(self.sigParameterChanged)

        DelayAfterLaser3Label = QtWidgets.QLabel('Delay after Laser 3 (ms)')
        self.DelayAfterLaser3Edit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.DelayAfterLaser3Edit.setMaximum(1000)
        self.DelayAfterLaser3Edit.editingFinished.connect(self.sigParameterChanged)

        Laser4OnLabel = QtWidgets.QLabel('Laser 4 on time (ms)')
        self.Laser4OnEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.Laser4OnEdit.editingFinished.connect(self.sigParameterChanged)

        DelayAfterLaser4Label = QtWidgets.QLabel('Delay after Laser 4 (ms)')
        self.DelayAfterLaser4Edit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.DelayAfterLaser4Edit.setMaximum(1000)
        self.DelayAfterLaser4Edit.editingFinished.connect(self.sigParameterChanged)

        Laser5OnLabel = QtWidgets.QLabel('Laser 5 on time (ms)')
        self.Laser5OnEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.Laser5OnEdit.editingFinished.connect(self.sigParameterChanged)

        DelayAfterLaser5Label = QtWidgets.QLabel('Delay after Laser 5 (ms)')
        self.DelayAfterLaser5Edit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.DelayAfterLaser5Edit.setMaximum(1000)
        self.DelayAfterLaser5Edit.editingFinished.connect(self.sigParameterChanged)

        MulticolorScanFirstLabel = QtWidgets.QLabel('Multicolor scan first position (V)')
        self.MulticolorScanFirstEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.MulticolorScanFirstEdit.setMinimum(-500)
        self.MulticolorScanFirstEdit.setMaximum(500)
        self.MulticolorScanFirstEdit.editingFinished.connect(self.sigParameterChanged)

        MulticolorScanSecondLabel = QtWidgets.QLabel('Multicolor scan second position (V)')
        self.MulticolorScanSecondEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.MulticolorScanSecondEdit.setMinimum(-500)
        self.MulticolorScanSecondEdit.setMaximum(500)
        self.MulticolorScanSecondEdit.editingFinished.connect(self.sigParameterChanged)


        roRestingPosUmLabel = QtWidgets.QLabel('RO scan resting position (um)')
        self.roRestingPosUmEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.roRestingPosUmEdit.setMinimum(-200)
        self.roRestingPosUmEdit.setMaximum(200)
        self.roRestingPosUmEdit.editingFinished.connect(self.sigParameterChanged)

        roStartPosUmLabel = QtWidgets.QLabel('RO scan start (um)')
        self.roStartPosUmEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.roStartPosUmEdit.setMinimum(-200)
        self.roStartPosUmEdit.setMaximum(200)
        self.roStartPosUmEdit.editingFinished.connect(self.sigParameterChanged)

        roStepSizeUmLabel = QtWidgets.QLabel('RO scan step size (um)')
        self.roStepSizeUmEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.roStepSizeUmEdit.setMinimum(-200)
        self.roStepSizeUmEdit.setMaximum(200)
        self.roStepSizeUmEdit.editingFinished.connect(self.sigParameterChanged)

        roStepsLabel = QtWidgets.QLabel('RO scan steps')
        self.roStepsEdit = guitools.BetterSpinBox(allowScrollChanges=False)
        self.roStepsEdit.setMaximum(10000)
        self.roStepsEdit.editingFinished.connect(self.sigParameterChanged)

        cycleStartPosUmLabel = QtWidgets.QLabel('Cycle scan start (um)')
        self.cycleStartPosUmEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.cycleStartPosUmEdit.setMinimum(-200)
        self.cycleStartPosUmEdit.setMaximum(200)
        self.cycleStartPosUmEdit.editingFinished.connect(self.sigParameterChanged)

        cycleStepSizeUmLabel = QtWidgets.QLabel('Cycle scan step size (um)')
        self.cycleStepSizeUmEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.cycleStepSizeUmEdit.setMinimum(-10)
        self.cycleStepSizeUmEdit.setMaximum(10)
        self.cycleStepSizeUmEdit.setDecimals(3)
        self.cycleStepSizeUmEdit.editingFinished.connect(self.sigParameterChanged)

        cycleStepsLabel = QtWidgets.QLabel('Cycle scan steps')
        self.cycleStepsEdit = guitools.BetterSpinBox(allowScrollChanges=False)
        self.cycleStepsEdit.setMaximum(1000)
        self.cycleStepsEdit.editingFinished.connect(self.sigParameterChanged)

        Laser1Label = QtWidgets.QLabel('Laser 1')
        self.Laser1Edit = guitools.BetterComboBox(allowScrollChanges=False)

        Laser2Label = QtWidgets.QLabel('Laser 2')
        self.Laser2Edit = guitools.BetterComboBox(allowScrollChanges=False)

        Laser3Label = QtWidgets.QLabel('Laser 3')
        self.Laser3Edit = guitools.BetterComboBox(allowScrollChanges=False)

        Laser4Label = QtWidgets.QLabel('Laser 4')
        self.Laser4Edit = guitools.BetterComboBox(allowScrollChanges=False)

        Laser5Label = QtWidgets.QLabel('Laser 5')
        self.Laser5Edit = guitools.BetterComboBox(allowScrollChanges=False)


        CameraTTLLabel = QtWidgets.QLabel('Camera used for detection')
        self.CameraTTLEdit = guitools.BetterComboBox(allowScrollChanges=False)

        roScanDeviceLabel = QtWidgets.QLabel('RO scan device')
        self.roScanDeviceEdit = guitools.BetterComboBox(allowScrollChanges=False)

        MulticolorScanDeviceLabel = QtWidgets.QLabel('Multicolor scan device')
        self.MulticolorScanDeviceEdit = guitools.BetterComboBox(allowScrollChanges=False)



        cycleScanDeviceLabel = QtWidgets.QLabel('Cycle scan device is now hard coded same as RO-device')
        self.cycleScanDeviceEdit = guitools.BetterComboBox(allowScrollChanges=False)

        # Temp fix
        self.cycleScanDeviceEdit.setEnabled(False)

        currentRow = 0

        # Add space item to make the grid look nicer
        self.grid.addItem(
            QtWidgets.QSpacerItem(20, 40,
                                  QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
            currentRow, 0, 1, -1
        )
        currentRow += 1

        # Add scanner label
        self.grid.addWidget(self.scannerLabel, currentRow, 0)
        currentRow += 1

        # Add general buttons
        self.grid.addWidget(self.loadScanBtn, currentRow, 0)
        self.grid.addWidget(self.saveScanBtn, currentRow, 1)
        self.grid.addItem(
            QtWidgets.QSpacerItem(40, 20,
                                  QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum),
            currentRow, 3
        )
        self.grid.addWidget(autoStartRecLabel, currentRow, 2)
        self.grid.addWidget(self.autoStartRec, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(autoStopRecLabel, currentRow, 2)
        self.grid.addWidget(self.autoStopRec, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(self.scanButton, currentRow, 3)
        currentRow += 1
        self.grid.addItem(
            QtWidgets.QSpacerItem(40, 20,
                                  QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
            currentRow, 0, 1, 4)
        currentRow += 1
        self.grid.addWidget(timeLapsePointsLabel, currentRow, 0)
        self.grid.addWidget(self.timeLapsePointsEdit, currentRow, 1)
        self.grid.addWidget(timeLapseDelayLabel, currentRow, 2)
        self.grid.addWidget(self.timeLapseDelayEdit, currentRow, 3)
        currentRow += 1
        self.grid.addItem(
            QtWidgets.QSpacerItem(40, 20,
                                  QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
            currentRow, 0, 1, 4)
        currentRow += 1
        self.grid.addWidget(Laser1OnLabel, currentRow, 0)
        self.grid.addWidget(self.Laser1OnEdit, currentRow, 1)
        self.grid.addWidget(roRestingPosUmLabel, currentRow, 2)
        self.grid.addWidget(self.roRestingPosUmEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(DelayAfterLaser1Label, currentRow, 0)
        self.grid.addWidget(self.DelayAfterLaser1Edit, currentRow, 1)
        self.grid.addWidget(roStartPosUmLabel, currentRow, 2)
        self.grid.addWidget(self.roStartPosUmEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(Laser2OnLabel, currentRow, 0)
        self.grid.addWidget(self.Laser2OnEdit, currentRow, 1)
        self.grid.addWidget(roStepSizeUmLabel, currentRow, 2)
        self.grid.addWidget(self.roStepSizeUmEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(DelayAfterLaser2Label, currentRow, 0)
        self.grid.addWidget(self.DelayAfterLaser2Edit, currentRow, 1)
        self.grid.addWidget(roStepsLabel, currentRow, 2)
        self.grid.addWidget(self.roStepsEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(Laser3OnLabel, currentRow, 0)
        self.grid.addWidget(self.Laser3OnEdit, currentRow, 1)
        self.grid.addWidget(cycleStartPosUmLabel, currentRow, 2)
        self.grid.addWidget(self.cycleStartPosUmEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(DelayAfterLaser3Label, currentRow, 0)
        self.grid.addWidget(self.DelayAfterLaser3Edit, currentRow, 1)
        self.grid.addWidget(cycleStepSizeUmLabel, currentRow, 2)
        self.grid.addWidget(self.cycleStepSizeUmEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(Laser4OnLabel, currentRow, 0)
        self.grid.addWidget(self.Laser4OnEdit, currentRow, 1)
        self.grid.addWidget(cycleStepsLabel, currentRow, 2)
        self.grid.addWidget(self.cycleStepsEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(DelayAfterLaser4Label, currentRow, 0)
        self.grid.addWidget(self.DelayAfterLaser4Edit, currentRow, 1)
        self.grid.addWidget(Laser5OnLabel, currentRow, 2)
        self.grid.addWidget(self.Laser5OnEdit, currentRow, 3)

        currentRow += 1
        self.grid.addWidget(MulticolorScanFirstLabel, currentRow, 0)
        self.grid.addWidget(self.MulticolorScanFirstEdit, currentRow, 1)
        self.grid.addWidget(MulticolorScanSecondLabel, currentRow, 2)
        self.grid.addWidget(self.MulticolorScanSecondEdit, currentRow, 3)
        currentRow += 1
        self.grid.addItem(
            QtWidgets.QSpacerItem(40, 20,
                                  QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
            currentRow, 0, 1, 4)
        currentRow += 1
        self.grid.addWidget(Laser1Label, currentRow, 0)
        self.grid.addWidget(self.Laser1Edit, currentRow, 1)
        self.grid.addWidget(roScanDeviceLabel, currentRow, 2)
        self.grid.addWidget(self.roScanDeviceEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(Laser2Label, currentRow, 0)
        self.grid.addWidget(self.Laser2Edit, currentRow, 1)
        self.grid.addWidget(MulticolorScanDeviceLabel, currentRow, 2)
        self.grid.addWidget(self.MulticolorScanDeviceEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(Laser3Label, currentRow, 0)
        self.grid.addWidget(self.Laser3Edit, currentRow, 1)
        self.grid.addWidget(Laser5Label, currentRow, 2)
        self.grid.addWidget(self.Laser5Edit, currentRow, 3)
        currentRow +=1
        self.grid.addWidget(Laser4Label, currentRow, 0)
        self.grid.addWidget(self.Laser4Edit, currentRow, 1)
        self.grid.addWidget(CameraTTLLabel, currentRow, 2)
        self.grid.addWidget(self.CameraTTLEdit, currentRow, 3)
        currentRow +=1
        self.grid.addWidget(cycleScanDeviceLabel, currentRow, 2)
        self.grid.addWidget(self.cycleScanDeviceEdit, currentRow, 3)


        # Connect signals
        self.saveScanBtn.clicked.connect(self.sigSaveScanClicked)
        self.loadScanBtn.clicked.connect(self.sigLoadScanClicked)
        self.scanButton.clicked.connect(self.sigRunScanClicked)


    def getTimeLapsePoints(self):
        return self.timeLapsePointsEdit.value()

    def setTimeLapsePoints(self, value):
        self.timeLapsePointsEdit.setValue(value)

    def getTimeLapseDelayS(self):
        return self.timeLapseDelayEdit.value()

    def setTimeLapseDelayS(self, value):
        self.timeLapseDelayEdit.setValue(value)

    def getLaser1OnMs(self):
        return self.Laser1OnEdit.value()

    def setLaser1OnMs(self, value):
        self.Laser1OnEdit.setValue(value)

    def getDelayAfterLaser1Ms(self):
        return self.DelayAfterLaser1Edit.value()

    def setDelayAfterLaser1Ms(self, value):
        self.DelayAfterLaser1Edit.setValue(value)

    def getLaser2OnMs(self):
        return self.Laser2OnEdit.value()

    def setLaser2OnMs(self, value):
        self.Laser2OnEdit.setValue(value)

    def getDelayAfterLaser2Ms(self):
        return self.DelayAfterLaser2Edit.value()

    def setDelayAfterLaser2Ms(self, value):
        self.DelayAfterLaser2Edit.setValue(value)
        
    def getLaser3OnMs(self):
        return self.Laser3OnEdit.value()

    def setLaser3OnMs(self, value):
        self.Laser3OnEdit.setValue(value)

    def getDelayAfterLaser3Ms(self):
        return self.DelayAfterLaser3Edit.value()

    def setDelayAfterLaser3Ms(self, value):
        self.DelayAfterLaser3Edit.setValue(value)
        
    def getLaser4OnMs(self):
        return self.Laser4OnEdit.value()

    def setLaser4OnMs(self, value):
        self.Laser4OnEdit.setValue(value)

    def getDelayAfterLaser4Ms(self):
        return self.DelayAfterLaser4Edit.value()

    def setDelayAfterLaser4Ms(self, value):
        self.DelayAfterLaser4Edit.setValue(value)
        
    def getLaser5OnMs(self):
        return self.Laser5OnEdit.value()

    def setLaser5OnMs(self, value):
        self.Laser5OnEdit.setValue(value)

    def getDelayAfterLaser5Ms(self):
        return self.DelayAfterLaser5Edit.value()

    def setDelayAfterLaser5Ms(self, value):
        self.DelayAfterLaser5Edit.setValue(value)


    def getRoRestingPosUm(self):
        return self.roRestingPosUmEdit.value()

    def setRoRestingPosUm(self, value):
        self.roRestingPosUmEdit.setValue(value)

    def getMulticolorScanFirstUm(self):
        return self.MulticolorScanFirstEdit.value()

    def setMulticolorScanFirstUm(self, value):
        self.MulticolorScanFirstEdit.setValue(value)

    def getMulticolorScanSecondUm(self):
        return self.MulticolorScanSecondEdit.value()

    def setMulticolorScanSecondUm(self, value):
        self.MulticolorScanSecondEdit.setValue(value)

    def getRoStartPosUm(self):
        return self.roStartPosUmEdit.value()

    def setRoStartPosUm(self, value):
        self.roStartPosUmEdit.setValue(value)

    def getRoStepSizeUm(self):
        return self.roStepSizeUmEdit.value()

    def setRoStepSizeUm(self, value):
        self.roStepSizeUmEdit.setValue(value)

    def getRoSteps(self):
        return self.roStepsEdit.value()

    def setRoSteps(self, value):
        self.roStepsEdit.setValue(value)

    def getCycleStartPosUm(self):
        return self.cycleStartPosUmEdit.value()

    def setCycleStartPosUm(self, value):
        self.cycleStartPosUmEdit.setValue(value)


    def getCycleStepSizeUm(self):
        return self.cycleStepSizeUmEdit.value()

    def setCycleStepSizeUm(self, value):
        self.cycleStepSizeUmEdit.setValue(value)

    def getCycleSteps(self):
        return self.cycleStepsEdit.value()

    def setCycleSteps(self, value):
        self.cycleStepsEdit.setValue(value)

    def getLaser1(self):
        return self.Laser1Edit.currentText()

    def setLaser1(self, value):
        ind = self.Laser1Edit.findText(value)
        self.Laser1Edit.setCurrentIndex(ind)

    def getLaser2(self):
        return self.Laser2Edit.currentText()

    def setLaser2(self, value):
        ind = self.Laser2Edit.findText(value)
        self.Laser2Edit.setCurrentIndex(ind)

    def getLaser3(self):
        return self.Laser3Edit.currentText()

    def setLaser3(self, value):
        ind = self.Laser3Edit.findText(value)
        self.Laser3Edit.setCurrentIndex(ind)

    def getLaser4(self):
        return self.Laser4Edit.currentText()

    def setLaser4(self, value):
        ind = self.Laser4Edit.findText(value)
        self.Laser4Edit.setCurrentIndex(ind)
    
    def getLaser5(self):
        return self.Laser5Edit.currentText()

    def setLaser5(self, value):
        ind = self.Laser5Edit.findText(value)
        self.Laser5Edit.setCurrentIndex(ind)

    def getCameraTTL(self):
        return self.CameraTTLEdit.currentText()

    def setCameraTTL(self, value):
        ind = self.CameraTTLEdit.findText(value)
        self.CameraTTLEdit.setCurrentIndex(ind)


    def getRoLaser(self):
        return self.roLaserEdit.currentText()

    def setRoLaser(self, value):
        ind = self.roLaserEdit.findText(value)
        self.roLaserEdit.setCurrentIndex(ind)

    def getRoScanDevice(self):
        return self.roScanDeviceEdit.currentText()

    def setRoScanDevice(self, value):
        ind = self.roScanDeviceEdit.findText(value)
        self.roScanDeviceEdit.setCurrentIndex(ind)



    def getMulticolorScanDevice(self):
        return self.MulticolorScanDeviceEdit.currentText()

    def setMulticolorScanDevice(self, value):
        ind = self.MulticolorScanDeviceEdit.findText(value)
        self.MulticolorScanDeviceEdit.setCurrentIndex(ind)


    def getCycleScanDevice(self):
        return self.cycleScanDeviceEdit.currentText()

    def setCycleScanDevice(self, value):
        ind = self.cycleScanDeviceEdit.findText(value)
        self.cycleScanDeviceEdit.setCurrentIndex(ind)


    def setScanButtonChecked(self, checked):
        self.scanButton.setEnabled(not checked)
        self.scanButton.setCheckable(checked)
        self.scanButton.setChecked(checked)



    def plotSignalGraph(self, areas, signals, colors):
        if len(areas) != len(signals) or len(signals) != len(colors):
            raise ValueError('Arguments "areas", "signals" and "colors" must be of equal length')

        self.graph.plot.clear()
        for i in range(len(areas)):
            self.graph.plot.plot(areas[i], signals[i], pen=pg.mkPen(colors[i]))

        self.graph.plot.setYRange(-0.1, 1.1)

    def eventFilter(self, source, event):
        if source is self.gridContainer and event.type() == QtCore.QEvent.Resize:
            # Set correct minimum width (otherwise things can go outside the widget because of the
            # scroll area)
            width = self.gridContainer.minimumSizeHint().width() \
                    + self.scrollArea.verticalScrollBar().width()
            self.scrollArea.setMinimumWidth(width)
            self.setMinimumWidth(width)

        return False


class GraphFrame(pg.GraphicsLayoutWidget):
    """Creates the plot that plots the preview of the pulses."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plot = self.addPlot(row=1, col=0)


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
