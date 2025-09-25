"""Inspired from etMonalisaWidget"""


import os
#from inspect import signature
from imswitch.imcommon.model import initLogger

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

from imswitch.imcommon.model import dirtools
from imswitch.imcontrol.view import guitools
from imswitch.imcommon.view.guitools import naparitools
from .basewidgets import Widget#, NapariHybridWidget

_etSnoutyDir = "C:/Users/Snouty/imcontrol_etsnouty"


class EtSnoutyWidget(Widget):
    """ Widget for controlling the etSnouty implementation. """

    sigSavePipelineClicked = QtCore.Signal()
    sigLoadPipelineClicked = QtCore.Signal()


    def __init__(self, *args, **kwargs):
        self.__logger = initLogger(self, instanceName='EtSnoutyWidget')
        super().__init__(*args, **kwargs)

        self.analysisDir = os.path.join(_etSnoutyDir, 'analysis_pipelines')
        self.transformDir = os.path.join(_etSnoutyDir, 'transform_pipelines')


        #ROI
        #self.ROI.sigROIChanged.connect(self.sigROIChanged)


        if not os.path.exists(self.analysisDir):
            os.makedirs(self.analysisDir)

        if not os.path.exists(self.transformDir):
            os.makedirs(self.transformDir)

        # add scatterplot to napari imageviewer to plot the detected coordinates 
        self.eventScatterPlot = naparitools.VispyScatterVisual(color='red', symbol='x')
        self.eventScatterPlot.hide()
        
        # add all available analysis pipelines to a dropdown list
        self.analysisPipelines = list()
        self.analysisPipelinePar = QtGui.QComboBox()
        for pipeline in os.listdir(self.analysisDir):
            if os.path.isfile(os.path.join(self.analysisDir, pipeline)):
                pipeline = pipeline.split('.')[0]
                self.analysisPipelines.append(pipeline)
        
        self.analysisPipelinePar.addItems(self.analysisPipelines)
        self.analysisPipelinePar.setCurrentIndex(0)

        self.__paramsExclude = ['img', 'prev_frames', 'binary_mask', 'exinfo', 'testmode']
        

        

        # add all forAcquisition detectors in a dropdown list, for being the fastImgDetector (widefield)
        self.fastImgDetectors = list()
        self.fastImgDetectorsPar = QtGui.QComboBox()
        self.fastImgDetectorsPar_label = QtGui.QLabel('Fast detector')
        self.fastImgDetectorsPar_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        # add all lasers in a dropdown list, for being the fastImgLaser (widefield)
        self.fastImgLasers = list()
        self.fastImgLasersPar = QtGui.QComboBox()
        self.fastImgLasersPar_label = QtGui.QLabel('Fast laser, power(mW)')
        self.fastImgLasersPar_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        self.fastImgLasersPower_edit = QtGui.QLineEdit(str(30))



        # add all experiment modes in a dropdown list
        self.experimentModes = ['Experiment','TestVisualize','TestValidate']
        self.experimentModesPar = QtGui.QComboBox()
        self.experimentModesPar_label = QtGui.QLabel('Experiment mode')
        self.experimentModesPar_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignCenter)
        self.experimentModesPar.addItems(self.experimentModes)
        self.experimentModesPar.setCurrentIndex(0)


        self.param_names = list()
        self.param_edits = list()

        self.savePipelineParamsBtn = guitools.BetterPushButton('Save pipeline parameters')
        self.loadPipelineParamsBtn = guitools.BetterPushButton('Load pipeline parameters')


        self.initiateButton = guitools.BetterPushButton('Initiate etSnouty')
        self.initiateButton.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        self.loadPipelineButton = guitools.BetterPushButton('Load pipeline')

        self.recordBinaryMaskButton = guitools.BetterPushButton('Record binary mask')
        self.loadBinaryMaskButton = guitools.BetterPushButton('Load binary mask')
        self.clearBinaryMaskButton = guitools.BetterPushButton('Clear binary mask')
        self.showBinaryMaskButton = guitools.BetterPushButton('Show binary mask')



        #self.setUpdatePeriodButton = guitools.BetterPushButton('Set update period')
        self.setUpdatePeriodCheck = QtGui.QCheckBox('Use Widefield camera frameRate')
        self.TestModeCheck = QtGui.QCheckBox('Test Mode')
        self.setBusyFalseButton = guitools.BetterPushButton('Unlock softlock')


        self.endlessScanCheck = QtGui.QCheckBox('Endless')


        self.update_period_label = QtGui.QLabel('Update period (ms)')
        self.update_period_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        self.update_period_edit = QtGui.QLineEdit(str(100))





        # help widget for showing images from the analysis pipelines, i.e. binary masks or analysed images in live
        self.analysisHelpWidget = AnalysisWidget(*args, **kwargs)

        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)

        # initialize widget controls
        currentRow = 0

        self.grid.addWidget(self.initiateButton, currentRow, 0)
        self.grid.addWidget(self.endlessScanCheck, currentRow, 1)
        self.grid.addWidget(self.experimentModesPar_label, currentRow, 2)
        self.grid.addWidget(self.experimentModesPar, currentRow, 3)
        self.grid.addWidget(self.setBusyFalseButton, currentRow, 4)

        currentRow += 1

        self.grid.addWidget(self.loadPipelineButton, currentRow, 0)
        self.grid.addWidget(self.analysisPipelinePar, currentRow, 1)

        self.grid.addWidget(self.loadBinaryMaskButton, currentRow, 3)

        self.grid.addWidget(self.recordBinaryMaskButton, currentRow, 4)


        currentRow += 1
        self.grid.addWidget(self.loadPipelineParamsBtn, currentRow, 0)
        self.grid.addWidget(self.savePipelineParamsBtn, currentRow, 1)

        self.grid.addWidget(self.clearBinaryMaskButton, currentRow, 3)
        self.grid.addWidget(self.showBinaryMaskButton, currentRow, 4)


        currentRow += 1

        self.grid.addWidget(self.update_period_label, currentRow, 2)
        self.grid.addWidget(self.update_period_edit, currentRow, 3)
        self.grid.addWidget(self.setUpdatePeriodCheck, currentRow, 4)

        currentRow +=1

        self.grid.addWidget(self.fastImgDetectorsPar_label, currentRow, 2)
        self.grid.addWidget(self.fastImgDetectorsPar, currentRow, 3)
        self.grid.addWidget(self.TestModeCheck, currentRow, 4)

        currentRow += 1

        self.grid.addWidget(self.fastImgLasersPar_label, currentRow, 2)
        self.grid.addWidget(self.fastImgLasersPar, currentRow, 3)

        self.grid.addWidget(self.fastImgLasersPower_edit, currentRow, 4)


        #connect signals
        self.savePipelineParamsBtn.clicked.connect(self.sigSavePipelineClicked)
        self.loadPipelineParamsBtn.clicked.connect(self.sigLoadPipelineClicked)


    def initParamFields(self, parameters: dict):
        """ Initialized etMonalisa widget parameter fields. """
        # remove previous parameter fields for the previously loaded pipeline
        for param in self.param_names:
            self.grid.removeWidget(param)
            param.deleteLater()
        for param in self.param_edits:
            self.grid.removeWidget(param)
            param.deleteLater()

        # initiate parameter fields for all the parameters in the pipeline chosen
        currentRow = 3
        
        self.param_names = list()
        self.param_edits = list()
        for pipeline_param_name, pipeline_param_val in parameters.items():
            if pipeline_param_name not in self.__paramsExclude:
                # create param for input
                param_name = QtGui.QLabel('{}'.format(pipeline_param_name))
                param_value = pipeline_param_val.default if pipeline_param_val.default is not pipeline_param_val.empty else 0
                param_edit = QtGui.QLineEdit(str(param_value))
                # add param name and param to grid
                self.grid.addWidget(param_name, currentRow, 0)
                self.grid.addWidget(param_edit, currentRow, 1)
                # add param name and param to object list of temp widgets
                self.param_names.append(param_name)
                self.param_edits.append(param_edit)

                currentRow += 1

    def setFastDetectorList(self, detectorNames):
        """ Set combobox with available detectors to use for the fast method. """
        for detectorName, _ in detectorNames.items():
            self.fastImgDetectors.append(detectorName)
        self.fastImgDetectorsPar.addItems(self.fastImgDetectors)
        self.fastImgDetectorsPar.setCurrentIndex(0)

    def setFastLaserList(self, laserNames):
        """ Set combobox with available lasers to use for the fast method. """
        for laserName, _ in laserNames.items():
            self.fastImgLasers.append(laserName)
        self.fastImgLasersPar.addItems(self.fastImgLasers)
        self.fastImgLasersPar.setCurrentIndex(0)


    def setEventScatterData(self, x, y):
        """ Updates scatter plot of detected coordinates with new data. """
        self.eventScatterPlot.setData(x=x, y=y)
        
    def setEventScatterVisible(self, visible):
        """ Updates visibility of scatter plot. """
        pass
        #self.eventScatterPlot.setVisible(visible)

    def getEventScatterPlot(self):
        return self.eventScatterPlot

    def launchHelpWidget(self, widget, init=True):
        """ Launch the help widget. """
        if init:
            widget.show()
        else:
            widget.hide()


    def getROIGraphicsItem(self):
        return self.ROI

    def showROI(self, position=None, size=None):
        if position is not None:
            self.ROI.position = position
        if size is not None:
            self.ROI.size = size
        self.ROI.show()

    def hideROI(self):
        self.ROI.hide()


class AnalysisWidget(Widget):
    """ Pop-up widget for the live analysis images or binary masks. """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.imgVbWidget = pg.GraphicsLayoutWidget()
        self.imgVb = self.imgVbWidget.addViewBox(row=1, col=1)

        self.img = pg.ImageItem(axisOrder = 'row-major')
        self.img.translate(-0.5, -0.5)

        self.scatter = pg.ScatterPlotItem()

        self.imgVb.addItem(self.img)
        self.imgVb.setAspectLocked(True)
        self.imgVb.addItem(self.scatter)

        self.info_label = QtGui.QLabel('<image info>')
        
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.grid.addWidget(self.info_label, 0, 0)
        self.grid.addWidget(self.imgVbWidget, 1, 0)

