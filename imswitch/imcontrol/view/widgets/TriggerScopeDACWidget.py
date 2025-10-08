from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget


class TriggerScopeDAC(Widget):
    """ Widget in control of the DAC voltage. """

    sigStepUpClicked = QtCore.Signal(str, str)  # (positionerName, axis)
    sigStepDownClicked = QtCore.Signal(str, str)  # (positionerName, axis)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.numDACChannels = 0
        self.pars = {}
        self.grid = QtWidgets.QGridLayout()
        self.setLayout(self.grid)

    def addDACChannel(self, DACChannelName, axes):
        for i in range(len(axes)):
            axis = axes[i]
            parNameSuffix = self._getParNameSuffix(DACChannelName, axis)
            label = f'{DACChannelName} -- {axis}' if DACChannelName != axis else DACChannelName

            self.pars['Label' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{label}</strong>')
            self.pars['Label' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
            self.pars['Position' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{0:.2f} V</strong>')
            self.pars['Position' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
            self.pars['UpButton' + parNameSuffix] = guitools.BetterPushButton('+')
            self.pars['DownButton' + parNameSuffix] = guitools.BetterPushButton('-')
            self.pars['StepEdit' + parNameSuffix] = QtWidgets.QLineEdit('0.1')
            self.pars['StepUnit' + parNameSuffix] = QtWidgets.QLabel(' V')

            self.grid.addWidget(self.pars['Label' + parNameSuffix], self.numDACChannels, 0)
            self.grid.addWidget(self.pars['Position' + parNameSuffix], self.numDACChannels, 1)
            self.grid.addWidget(self.pars['UpButton' + parNameSuffix], self.numDACChannels, 2)
            self.grid.addWidget(self.pars['DownButton' + parNameSuffix], self.numDACChannels, 3)
            self.grid.addWidget(QtWidgets.QLabel('Step'), self.numDACChannels, 4)
            self.grid.addWidget(self.pars['StepEdit' + parNameSuffix], self.numDACChannels, 5)
            self.grid.addWidget(self.pars['StepUnit' + parNameSuffix], self.numDACChannels, 6)

            self.numDACChannels += 1

            # Connect signals
            self.pars['UpButton' + parNameSuffix].clicked.connect(
                lambda *args, axis=axis: self.sigStepUpClicked.emit(DACChannelName, axis)
            )
            self.pars['DownButton' + parNameSuffix].clicked.connect(
                lambda *args, axis=axis: self.sigStepDownClicked.emit(DACChannelName, axis)
            )

    def getStepSize(self, DACChannelName, axis):
        """ Returns the step size of the specified positioner axis in
        micrometers. """
        parNameSuffix = self._getParNameSuffix(DACChannelName, axis)
        return float(self.pars['StepEdit' + parNameSuffix].text())

    def setStepSize(self, DACChannelName, axis, stepSize):
        """ Sets the step size of the specified positioner axis to the
        specified number of micrometers. """
        parNameSuffix = self._getParNameSuffix(DACChannelName, axis)
        self.pars['StepEdit' + parNameSuffix].setText(stepSize)

    def updatePosition(self, DACChannelName, axis, position):
        parNameSuffix = self._getParNameSuffix(DACChannelName, axis)
        self.pars['Position' + parNameSuffix].setText(f'<strong>{position:.2f} V</strong>')

    def _getParNameSuffix(self, DACChannelName, axis):
        return f'{DACChannelName}--{axis}'


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
