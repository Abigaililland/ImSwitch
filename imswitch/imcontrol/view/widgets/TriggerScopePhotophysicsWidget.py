import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget


class TriggerScopePhotophysicsWidget(Widget):
    """ Widget containing scanner interface and beadscan reconstruction.
            This class uses the classes GraphFrame, MultipleScanWidget and IllumImageWidget"""

    sigSaveScanClicked = QtCore.Signal()
    sigLoadScanClicked = QtCore.Signal()
    sigRunScanClicked = QtCore.Signal()
    sigParameterChanged = QtCore.Signal()
    # sigOnTimeMsChanged = QtCore.Signal()
    # sigOffTimeMsChanged = QtCore.Signal()
    # sigdelayAfterOnTimeMsChanged = QtCore.Signal()
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
        self.scannerLabel = QtWidgets.QLabel('pLS-RESOLFT scanner')
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

        self.graph = GraphFrame()
        self.graph.setEnabled(False)
        self.graph.setFixedHeight(128)

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

        timeLapsePointsLabel = QtWidgets.QLabel('Number of cycles')
        self.timeLapsePointsEdit = guitools.BetterSpinBox(allowScrollChanges=False)
        self.timeLapsePointsEdit.editingFinished.connect(self.sigParameterChanged)

        timeLapseDelayLabel = QtWidgets.QLabel('Delay between cycles')
        self.timeLapseDelayEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.timeLapseDelayEdit.setMaximum(1000)
        self.timeLapseDelayEdit.editingFinished.connect(self.sigParameterChanged)


        onTimeLabel = QtWidgets.QLabel('On-pulse time (ms)')
        self.onTimeEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.onTimeEdit.setMaximum(1000)
        self.onTimeEdit.editingFinished.connect(self.sigParameterChanged)

        delayAfterOnLabel = QtWidgets.QLabel('Delay after on-pulse (ms)')
        self.delayAfterOnEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.delayAfterOnEdit.editingFinished.connect(self.sigParameterChanged)

        offTimeLabel = QtWidgets.QLabel('Off-pulse time (ms)')
        self.offTimeEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.offTimeEdit.setMaximum(1000)
        self.offTimeEdit.editingFinished.connect(self.sigParameterChanged)

        delayAfterOffLabel = QtWidgets.QLabel('Delay after off-pulse (ms)')
        self.delayAfterOffEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.delayAfterOffEdit.editingFinished.connect(self.sigParameterChanged)


        onLaserLabel = QtWidgets.QLabel('On laser')
        self.onLaserEdit = guitools.BetterComboBox(allowScrollChanges=False)

        offLaserLabel = QtWidgets.QLabel('Off laser')
        self.offLaserEdit = guitools.BetterComboBox(allowScrollChanges=False)


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
        graphRow = currentRow
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


        self.grid.addWidget(onTimeLabel, currentRow, 0)
        self.grid.addWidget(self.onTimeEdit, currentRow, 1)

        currentRow += 1
        self.grid.addWidget(delayAfterOnLabel, currentRow, 0)
        self.grid.addWidget(self.delayAfterOnEdit, currentRow, 1)
        currentRow += 1
        self.grid.addWidget(offTimeLabel, currentRow, 0)
        self.grid.addWidget(self.offTimeEdit, currentRow, 1)
        currentRow += 1
        self.grid.addWidget(delayAfterOffLabel, currentRow, 0)
        self.grid.addWidget(self.delayAfterOffEdit, currentRow, 1)
        currentRow += 1
        self.grid.addItem(
            QtWidgets.QSpacerItem(40, 20,
                                  QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
            currentRow, 0, 1, 4)
        currentRow += 1
        self.grid.addWidget(onLaserLabel, currentRow, 0)
        self.grid.addWidget(self.onLaserEdit, currentRow, 1)
        currentRow += 1
        self.grid.addWidget(offLaserLabel, currentRow, 0)
        self.grid.addWidget(self.offLaserEdit, currentRow, 1)
        self.grid.addWidget(cycleScanDeviceLabel, currentRow, 2)
        self.grid.addWidget(self.cycleScanDeviceEdit, currentRow, 3)
        currentRow+=1

        # Add pulse graph
        self.grid.addWidget(self.graph, graphRow, 2, currentRow - graphRow, 3)

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


    def getOnTimeMs(self):
        return self.onTimeEdit.value()

    def setOnTimeMs(self, value):
        self.onTimeEdit.setValue(value)

    def getDelayAfterOnTimeMs(self):
        return self.delayAfterOnEdit.value()

    def setDelayAfterOnTimeMs(self, value):
        self.delayAfterOnEdit.setValue(value)

    def getOffTimeMs(self):
        return self.offTimeEdit.value()

    def setOffTimeMs(self, value):
        self.offTimeEdit.setValue(value)

    def getDelayAfterOffTimeMs(self):
        return self.delayAfterOffEdit.value()

    def setDelayAfterOffTimeMs(self, value):
        self.delayAfterOffEdit.setValue(value)




    def getOnLaser(self):
        return self.onLaserEdit.currentText()

    def setOnLaser(self, value):
        ind = self.onLaserEdit.findText(value)
        self.onLaserEdit.setCurrentIndex(ind)

    def getOffLaser(self):
        return self.offLaserEdit.currentText()

    def setOffLaser(self, value):
        ind = self.offLaserEdit.findText(value)
        self.offLaserEdit.setCurrentIndex(ind)




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
