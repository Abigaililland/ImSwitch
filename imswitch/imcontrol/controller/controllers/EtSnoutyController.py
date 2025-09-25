"""Inspired from etMonalisaController"""



import configparser
import os
import sys
import ctypes
import importlib
import enum
from ast import literal_eval

import time
from collections import deque
from datetime import datetime
from inspect import signature

import imageio
import scipy.ndimage as ndi
import pyqtgraph as pg
import numpy as np
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from pyqtgraph import RectROI

from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import initLogger
from qtpy.QtCore import QObject, QTimer
from imswitch.imcontrol.view import guitools


_logsDir = "C:/Users/Snouty/imcontrol_etsnouty/recordings/logs_et"
_paramsDir = "C:/Users/Snouty/imcontrol_etsnouty/pipelinesParams"
_binaryMask = "C:/Users/Snouty/imcontrol_etsnouty/binaryMask"

def timestamp():
    """Return current time (s). High-res timing function adapted from:
    https://stackoverflow.com/questions/38319606/how-can-i-get-millisecond-and-microsecond-resolution-timestamps-in-python/38319607#38319607 """
    tics = ctypes.c_int64()
    freq = ctypes.c_int64()
    #get ticks on the internal ~2MHz QPC clock
    ctypes.windll.Kernel32.QueryPerformanceCounter(ctypes.byref(tics)) 
    #get the actual freq. of the internal ~2MHz QPC clock
    ctypes.windll.Kernel32.QueryPerformanceFrequency(ctypes.byref(freq))  
    return tics.value, freq.value 

def micros():
    "Return a timestamp in microseconds (us). "
    tics, freq = timestamp()
    return tics*1e6/freq
    
def millis():
    "Return a timestamp in milliseconds (ms). "
    tics, freq = timestamp()
    return tics*1e3/freq

class PeriodicSignalEmitter(QObject):
    def __init__(self, signal_to_emit, interval_ms=1000):

        super().__init__()
        self.signal_to_emit = signal_to_emit
        self.timer = QTimer()
        self.timer.setInterval(interval_ms)
        self.timer.timeout.connect(self.emit_signal)

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def emit_signal(self):
        self.signal_to_emit.emit()



class EtSnoutyController(ImConWidgetController):
    """ Linked to EtSnoutyWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self, instanceName="EtSnoutyController")

        self._widget.setFastDetectorList(
            self._master.detectorsManager.execOnAll(lambda c: c.name,
                                                    condition=lambda c: c.forAcquisition)
        )

        self._widget.setFastLaserList(
            self._master.lasersManager.execOnAll(lambda c: c.name)
        )


        sys.path.append(self._widget.analysisDir)
        sys.path.append(self._widget.transformDir)

        # Connect EtSnouty and communication channel signals
        self._widget.initiateButton.clicked.connect(self.initiate)
        self._widget.loadPipelineButton.clicked.connect(self.loadPipeline)
        self._widget.recordBinaryMaskButton.clicked.connect(self.initiateBinaryMask)
        self._widget.loadBinaryMaskButton.clicked.connect(self.loadBinaryMask)
        self._widget.clearBinaryMaskButton.clicked.connect(self.clearBinaryMask)
        self._widget.showBinaryMaskButton.clicked.connect(self.showBinaryMask)
        self._widget.setBusyFalseButton.clicked.connect(self.setBusyFalse)

        #load and save params
        self._widget.sigSavePipelineClicked.connect(self.savePipelineParams)
        self._widget.sigLoadPipelineClicked.connect(self.loadPipelineParams)

        # initiate log for each detected event
        self.resetDetLog()

        # initiate flags and params
        self.ClockWidefield = False
        self.__runMode = RunMode.Experiment
        self.__running = False
        self.__validating = False
        self.__busy = False
        self.__clock_busy = False;
        self.__prevFrames = deque(maxlen=10)
        self.__prevAnaFrames = deque(maxlen=10)
        self.__binary_mask = None
        self.__binary_stack = None
        self.__binary_frames = 10
        self.__init_frames = 5
        self.__validationFrames = 0
        self.__frame = 0
        self.__t_call = 0
        self.__maxAnaImgVal = 0
        self.__flipwfcalib = True  # flipping widefield image when loading for transformation calibration






    #To save and load the pipeline parameters

    def savePipelineParams(self):
        filePath = guitools.askForFilePath(self._widget, 'Save pipeline parameters', _paramsDir, isSaving=True)
        if filePath:
            self.savePipelineParamsToFile(filePath)

    def loadPipelineParams(self):
        filePath = guitools.askForFilePath(self._widget, 'Load pipeline parameters', _paramsDir)
        if filePath:
            self.loadPipelineParamsFromFile(filePath)



    def savePipelineParamsToFile(self, filePath: str) -> None:
        """Save actual parameters in a file."""
        config = configparser.ConfigParser()
        config.optionxform = str  # Respecter la casse

        # Extract parameters from widget
        pipeline_param_dict = {}
        for name_label, edit in zip(self._widget.param_names, self._widget.param_edits):
            param_name = name_label.text()
            param_value = edit.text()
            pipeline_param_dict[param_name] = param_value

        config['pipelineParameterDict'] = pipeline_param_dict

        with open(filePath, 'w') as configfile:
            config.write(configfile)

    def loadPipelineParamsFromFile(self, filePath: str) -> None:
        """load the parameters from a file"""
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(filePath)

        if 'pipelineParameterDict' not in config.sections():
            print(f"[Error] Section 'pipelineParameterDict' missing in the file : {filePath}")
            return

        pipeline_param_dict = config['pipelineParameterDict']


        for name_label, edit in zip(self._widget.param_names, self._widget.param_edits):
            param_name = name_label.text()
            if param_name in pipeline_param_dict:
                raw_value = pipeline_param_dict[param_name]
                try:
                    value = literal_eval(raw_value)
                except Exception:
                    value = raw_value
                edit.setText(str(value))








    def initiate(self):
        """ Initiate or stop an etMonalisa experiment. """


        if not self.__running:
            self.resetParamVals()
            self.resetRunParams()

            self._commChannel.sigInitiateEtSnouty.emit(True)

            detectorFastIdx = self._widget.fastImgDetectorsPar.currentIndex()
            self.detectorFast = self._widget.fastImgDetectors[detectorFastIdx]


            laserFastIdx = self._widget.fastImgLasersPar.currentIndex()
            self.laserFast = self._widget.fastImgLasers[laserFastIdx]
            self.laserFastpower = np.float(self._widget.fastImgLasersPower_edit.text())


            self.__param_vals = self.readParams()
            # Reset parameter for extra information that pipelines can input and output
            self.__exinfo = None

            # Check if visualization mode, in case launch help widget
            experimentModeIdx = self._widget.experimentModesPar.currentIndex()
            self.experimentMode = self._widget.experimentModes[experimentModeIdx]
            if self.experimentMode == 'TestVisualize':
                self.__runMode = RunMode.Visualize
            elif self.experimentMode == 'TestValidate':
                self.__runMode = RunMode.Validate
            else:
                self.__runMode = RunMode.Experiment
            # Switch to Widefild config if in experiment mode
            self.setConfig(widefield=True)
            self.detectorFast_controller = self._master.detectorsManager._subManagers[self.detectorFast]


            if self._widget.setUpdatePeriodCheck.isChecked():
                self.ClockWidefield = False
            else :
                self.ClockWidefield = True
                self.setUpdatePeriod()

            if self.__runMode == RunMode.Validate or self.__runMode == RunMode.Visualize:
                self.launchHelpWidget()

            if self.ClockWidefield:
                self._commChannel.sigClockWidefield.connect(self.clockWidefield_fct)
            else :
                self._commChannel.sigUpdateImage.connect(self.runPipeline)

            self._commChannel.sigToggleBlockScanWidget.emit(False)
            self._commChannel.sigScanEnded.connect(self.scanEnded)

            self._widget.initiateButton.setText('Stop')
            self.__running = True

        else:
            self._commChannel.sigInitiateEtSnouty.emit(False)

            # disconnect communication channel signals and turn off wf laser
            if self.ClockWidefield:
                self._commChannel.sigClockWidefield.disconnect(self.clockWidefield_fct)
            else:
                self._commChannel.sigUpdateImage.disconnect(self.runPipeline)

            self._commChannel.sigToggleBlockScanWidget.emit(True)
            self._commChannel.sigScanEnded.disconnect(self.scanEnded)

            self._master.lasersManager.execOn(self.laserFast, lambda l: l.setEnabled(False))
            #self._commChannel.sigSetLaserValue.emit(self.laserFast, 0) #Display on Laser Controller widget


            self._widget.initiateButton.setText('Initiate')
            self.resetParamVals()
            self.resetRunParams()


    def setConfig(self, widefield=True):


        if widefield :

                self._master.lasersManager.execOn(self.laserFast, lambda l: l.setEnabled(True))

                self._commChannel.sigSetConfig.emit('Widefield imaging')
                self._commChannel.sigSetVisibleLayers.emit((self.detectorFast,))

        if not widefield :
                self._master.lasersManager.execOn(self.laserFast, lambda l: l.setEnabled(False))

                self._commChannel.sigSetConfig.emit('Light sheet imaging')







    def scanEnded(self):
        """ End an etSTED slow method scan. """
        self.setDetLogLine("scan_end",datetime.now().strftime('%Ss%fus'))

        self._commChannel.sigSnapImg.emit()
        try:
            total_scan_time = self.scanInfoDict['scan_samples_total'] * 10e-6  # length (s) of total scan signal
            self.setDetLogLine("total_scan_time", total_scan_time)
        except:
            self._logger.info("Scan 'total_scan_time' not saved in log as 'scan_samples_total' not available in scanInfoDict using current signal designer.")

        self.endRecording()
        self.continueFastModality()
        self.__frame = 0

    def setDetLogLine(self, key, val, *args):
        if args:
            self.__detLog[f"{key}{args[0]}"] = val
        else:
            self.__detLog[key] = val

    def runSlowScan(self):
        """ Run a scan of the slow method (STED). """
        self.__detLog[f"scan_start"] = datetime.now().strftime('%Ss%fus')

        self.setConfig(widefield=False)
        self._master.lasersManager.execOn(self.laserFast, lambda l: l.setEnabled(True))

        self._commChannel.sigRunScanTriggerScopePLSRMulticolor.emit()


    def endRecording(self):
        """ Save an etSTED slow method scan. """
        self.setDetLogLine("pipeline", self.getPipelineName())
        self.logPipelineParamVals()
        # save log file with temporal info of trigger event

        filename = datetime.utcnow().strftime('%Hh%Mm%Ss%fus')
        name = os.path.join(_logsDir, filename) + '_log'
        log = [f'{key}: {self.__detLog[key]}' for key in self.__detLog]
        with open(f'{name}.txt', 'w') as f:
            [f.write(f'{st}\n') for st in log]
        self.resetDetLog()


    def getPipelineName(self):
        """ Get the name of the pipeline currently used. """
        pipelineidx = self._widget.analysisPipelinePar.currentIndex()
        pipelinename = self._widget.analysisPipelines[pipelineidx]
        return pipelinename

    def logPipelineParamVals(self):
        """ Put analysis pipeline parameter values in the log file. """
        params_ignore = ['img','prev_frames','binary_mask','testmode','exinfo']
        param_names = list()
        for pipeline_param_name, _ in self.__pipeline_params.items():
            if pipeline_param_name not in params_ignore:
                param_names.append(pipeline_param_name)
        for key, val in zip(param_names, self.__param_vals):
            self.setDetLogLine(key, val)

    def loadPipeline(self):
        """ Load the selected analysis pipeline, and its parameters into the GUI. """
        self.__pipelinename = self.getPipelineName()
        self.pipeline = getattr(importlib.import_module(f'{self.__pipelinename}'), f'{self.__pipelinename}')
        self.__pipeline_params = signature(self.pipeline).parameters
        self._widget.initParamFields(self.__pipeline_params)
    def getScanParameters(self):
        """ Load STED scan parameters from the scanning widget. """
        self._commChannel.sigRequestScanParameters.emit()
    def continueFastModality(self):
        print("continue")
        """ Continue the fast method, after an event scan has been performed. """
        if self._widget.endlessScanCheck.isChecked() and not self.__running:
            # switch back to FLUO mode if experiment mode
            self.setConfig(widefield=True)
            self._master.lasersManager.execOn(self.laserFast, lambda l: l.setEnabled(False))
            #time.sleep(0.1) #to ensure that next detected event is not just the LEDs turning on

            # connect communication channel signals
            self.updateScatter([], clear=True)#to clean the coord on the camera

            if self.ClockWidefield:
                self._commChannel.sigClockWidefield.connect(self.clockWidefield_fct)
            else:
                self._commChannel.sigUpdateImage.connect(self.runPipeline)

            self._widget.initiateButton.setText('Stop')
            self.__running = True

        elif not self._widget.endlessScanCheck.isChecked():
            self.updateScatter([], clear=True)#to clean the coord on the camera

            self._widget.initiateButton.setText('Initiate')

            self._commChannel.sigToggleBlockScanWidget.emit(True)
            self._commChannel.sigScanEnded.disconnect(self.scanEnded)

            self.__running = False
            self.resetParamVals()

    def setBusyFalse(self):
        self.__logger.debug("setBusyFalse")

        self.__busy = False;
        self.__clock_busy = False;


    def readParams(self):
        """ Read user-provided analysis pipeline parameter values. """
        param_vals = list()
        for item in self._widget.param_edits:
            param_vals.append(np.float(item.text()))
        return param_vals

    def launchHelpWidget(self):
        """ Launch help widget that shows the preprocessed images in real-time. """
        self._widget.launchHelpWidget(self._widget.analysisHelpWidget, init=True)

    def resetDetLog(self):
        """ Reset the event log file. """
        self.__detLog = dict()
        self.__detLog = {
            "pipeline": "",
            "pipeline_start": "",
            "pipeline_end": "",
            "coord_transf_start": "",
            "fastscan_x_center": 0,
            "fastscan_y_center": 0,
            "slowscan_x_center": 0,
            "slowscan_y_center": 0
        }

    def resetParamVals(self):
        self.__param_vals = list()

    def resetRunParams(self):
        self.__running = False
        self.__validating = False
        self.__frame = 0
        self.__maxAnaImgVal = 0
        self.__busy = False
        self.__clock_busy = False;
        self.__prevFrames.clear()
        self.__prevAnaFrames.clear()

    def runPipeline(self, detectorName, img, init=None, scale=None ):
        """ If detector is detectorFast and self.ClockWidefield = False : run the analyis pipeline, called after every fast method frame.
            If ClockWidefield = True : run the analyis pipeline, called by ClockWidefield_fct"""
        global i
        self.__logger.debug("runPipeline")
        del init, scale
        if detectorName == self.detectorFast:
            if not self.__busy:


                t_sincelastcall = millis() - self.__t_call
                self.__t_call = millis()
                self.setDetLogLine("pipeline_rep_period", str(t_sincelastcall))
                self.setDetLogLine("pipeline_start", datetime.now().strftime('%Ss%fus'))
                self.__busy = True

                if self.__prevFrames is None or len(self.__prevFrames)<=0:
                    self.__logger.debug("no prev_frames")

                try :
                    #t_pre = millis()
                    if self.__runMode == RunMode.Visualize or self.__runMode == RunMode.Validate:
                        coords_detected, self.__exinfo, img_ana = self.pipeline(img, self.__prevFrames, self.__binary_mask, (self.__runMode==RunMode.Visualize or self.__runMode==RunMode.Validate), self.__exinfo, *self.__param_vals)
                    elif self._widget.TestModeCheck.isChecked():
                        coords_detected, self.__exinfo, img_ana = self.pipeline(img, self.__prevFrames, self.__binary_mask, True, self.__exinfo, *self.__param_vals)
                    else :
                        coords_detected, self.__exinfo = self.pipeline(img, self.__prevFrames, self.__binary_mask, False, self.__exinfo, *self.__param_vals)


                    self.setDetLogLine("pipeline_end", datetime.now().strftime('%Ss%fus'))
                    #self._logger.debug(f'Pipeline time: {t_post-t_pre} ms')

                    if self.__frame > self.__init_frames:
                        # run if the initial frames have passed
                        if self.__runMode == RunMode.Visualize:
                            self.updateScatter(coords_detected, clear=True)
                            self.setAnalysisHelpImg(img_ana, self.__exinfo)
                        elif self.__runMode == RunMode.Validate:
                            self.updateScatter(coords_detected, clear=True)
                            self.setAnalysisHelpImg(img_ana)
                            if self.__validating:
                                if self.__validationFrames > 5:
                                    self.saveValidationImages(prev=True, prev_ana=True)
                                    self.pauseFastModality()
                                    self.endRecording()
                                    self.continueFastModality()
                                    self.__frame = 0
                                    self.__validating = False
                                self.__validationFrames += 1
                            elif coords_detected.size != 0:
                                # if some events where detected
                                if np.size(coords_detected) > 2:
                                    coords_wf = coords_detected[0,:]
                                else:
                                    coords_wf = coords_detected[0]
                                # log detected center coordinate
                                self.setDetLogLine("fastscan_x_center", coords_wf[0])
                                self.setDetLogLine("fastscan_y_center", coords_wf[1])
                                # log all detected coordinates
                                if np.size(coords_detected) > 2:
                                    for i in range(np.size(coords_detected,0)):
                                        self.setDetLogLine("det_coord_x_", coords_detected[i,0], i)
                                        self.setDetLogLine("det_coord_y_", coords_detected[i,1], i)
                                self.__validating = True
                                self.__validationFrames = 0

                        #if in experiment mode
                        elif coords_detected.size != 0:
                            # if some events were detected
                            if np.size(coords_detected) > 2:
                                coords_wf = np.copy(coords_detected[0,:])
                            else:
                                coords_wf = np.copy(coords_detected[0])
                            self.setDetLogLine("prepause", datetime.now().strftime('%Ss%fus'))
                            self.setDetLogLine("fastscan_x_center", coords_wf[0])
                            self.setDetLogLine("fastscan_y_center", coords_wf[1])
                            self.pauseFastModality()
                            self.setDetLogLine("coord_transf_start", datetime.now().strftime('%Ss%fus'))

                            self.setDetLogLine("scan_initiate", datetime.now().strftime('%Ss%fus'))
                            #save all detected coordinates in the log
                            if np.size(coords_detected) > 2:
                                for i in range(np.size(coords_detected,0)):
                                    self.setDetLogLine("det_coord_x_", coords_wf[0], i)
                                    self.setDetLogLine("det_coord_y_", coords_wf[1], i)


                            self.runSlowScan()

                            # update scatter plot of event coordinates in the shown fast method image
                            self.updateScatter(coords_detected, clear=True)
                            self.__prevFrames.append(img)


                            #self.saveValidationImages(prev=True, prev_ana=False)
                            #self.__exinfo = None
                            self.__busy = False
                            return


                    self.__prevFrames.append(img)
                    if self.__runMode == RunMode.Validate:
                        self.__prevAnaFrames.append(img_ana)
                    self.__frame += 1
                    self.setBusyFalse()
                finally :

                    try:
                        if self._widget.TestModeCheck.isChecked():
                            # Save the img
                            folder_path = _logsDir
                            file_name = f"frames/frame_{i}.png"
                            file_name2 = f"frames/frame_unmodif_{i}.png"
                            i += 1
                            full_path = os.path.join(folder_path, file_name)
                            full_path2 = os.path.join(folder_path, file_name2)
                            imageio.imwrite(full_path, img_ana)
                            imageio.imwrite(full_path2, img)
                            self.__logger.debug("saved")

                    except Exception:
                        self.__logger.debug("NOT SAVED")


                    self.setDetLogLine("pipeline_end", datetime.now().strftime('%Ss%fus'))
                    #self._logger.debug(f'Pipeline time: {t_post-t_pre} ms')

                    self.setBusyFalse()




    #Clock part and laser only during fat acquisition part
    def setUpdatePeriod(self):

        self._master.lasersManager.execOn(self.laserFast, lambda l: l.setEnabled(False))
        #self._commChannel.sigSetLaserValue.emit(self.laserFast, 0)  # Display on Laser Controller widget

        self.__logger.debug("setUpdatePeriod")
        self.ClockWidefield=True
        self.__updatePeriod = int(self._widget.update_period_edit.text())
        self.__logger.debug(self.__updatePeriod)
        self.emitter = PeriodicSignalEmitter(self._commChannel.sigClockWidefield, self.__updatePeriod)
        self.emitter.start()
        global i
        i=22


    def clockWidefield_fct(self):

        global i
        self.__logger.debug("clockWidefield_fct_busy ?")
        if not self.__clock_busy:
            self.__clock_busy=True;
            self.__logger.debug("clockWidefield_fct")




            self._master.lasersManager.execOn(self.laserFast, lambda l: l.setEnabled(True))

            time.sleep(0.5)

            img = self.detectorFast_controller.wait_and_get_NewFrame(True)

            self._master.lasersManager.execOn(self.laserFast, lambda l: l.setEnabled(False))


            # import tifffile as tf
            # path = "//storage3.ad.scilifelab.se/testalab/Abigail/Data_Calcium_15_05_2025/Calcium7/"
            # file = "Timelapse_40Frames_15s_noFilter_snap_WidefieldCamera_"
            # img = tf.imread(path + file + str(i) + ".tiff")

            self.runPipeline(self.detectorFast, img)





        else :
            self.__logger.debug("clockWidefield_fct called but already busy : update period may be too short")




    def setAnalysisHelpImg(self, img_ana, exinfo=None):
        """ Set the preprocessed image in the analysis help widget. """
        if np.max(img_ana) > self.__maxAnaImgVal:
            self.__maxAnaImgVal = np.max(img_ana)
            autolevels = True
        else:
            autolevels = False
        if img_ana.ndim == 3:
            img_ana = img_ana[0,:,:]
        self._widget.analysisHelpWidget.img.setImage(img_ana, autoLevels=autolevels)
        infotext = f'Min: {np.min(img_ana)}, max: {np.max(img_ana)}'
        self._widget.analysisHelpWidget.info_label.setText(infotext)

        # scatter plot exinfo if there is something (cdvesprox or dynamin)
        if exinfo is not None:
            if any(name in self.__pipelinename for name in ['cd_vesicle_prox', 'dynamin']):
                self._widget.analysisHelpWidget.scatter.setData(x=np.array(exinfo['y']), y=np.array(exinfo['x']), pen=pg.mkPen(None), brush='g', symbol='x', size=15)

        self._widget.analysisHelpWidget.img.render()


    def updateScatter(self, coords, clear=True):
        """ Update the scatter plot of detected event coordinates. """
        if clear:
            self._commChannel.sigRemoveItemFromVb.emit(self._widget.getEventScatterPlot())
        if np.size(coords) > 0:
            self._widget.setEventScatterData(x=coords[:,1],y=coords[:,0])
            # possibly not the below more than one time. Maybe it is enough to then update it, if the reference to the same object is kept throughout all function calls
            self._commChannel.sigAddItemToVb.emit(self._widget.getEventScatterPlot())

    def saveValidationImages(self, prev=True, prev_ana=True):
        """ Save the widefield validation images of an event detection. """
        if prev:
            img = np.array(list(self.__prevFrames))
            self._commChannel.sigSnapImgPrev.emit(self.detectorFast, img, 'raw')
            self.__prevFrames.clear()
        if prev_ana:
            img = np.array(list(self.__prevAnaFrames))
            self._commChannel.sigSnapImgPrev.emit(self.detectorFast, img, 'ana')
            self.__prevAnaFrames.clear()

    def pauseFastModality(self):
        """ Pause the fast method, when an event has been detected. """
        if self.__running:
            if self.ClockWidefield:
                self._commChannel.sigClockWidefield.disconnect(self.clockWidefield_fct)
            else:
                self._commChannel.sigUpdateImage.disconnect(self.runPipeline)
            self._master.lasersManager.execOn(self.laserFast, lambda l: l.setEnabled(False))
            #self._master.lasersManager.execOn(self.laserFast, lambda l: l.setValue(0))
            #self._commChannel.sigSetLaserValue.emit(self.laserFast, 0)  # Display on Laser Controller widget
            self.__running = False



    def initiateBinaryMask(self):

        detectorFastIdx = self._widget.fastImgDetectorsPar.currentIndex()
        self.detectorFast = self._widget.fastImgDetectors[detectorFastIdx]
        self.detectorFast_controller = self._master.detectorsManager._subManagers[self.detectorFast]

        time.sleep(1)
        self.latest_image = self.detectorFast_controller.getLatestFrame()
        # import tifffile as tf
        # path = "//storage3.ad.scilifelab.se/testalab/Abigail/Data_Calcium_15_05_2025/Calcium7/"
        # file = "Timelapse_40Frames_15s_noFilter_snap_WidefieldCamera_"
        # self.latest_image = tf.imread(path + file + str(29) + ".tiff")

        # graphical interface
        self.roi_win = pg.GraphicsLayoutWidget(title="Définir la ROI pour le masque")
        self.view = self.roi_win.addViewBox()
        self.view.setAspectLocked(True)

        self.img_item = pg.ImageItem(self.latest_image)
        self.view.addItem(self.img_item)

        # ROI
        self.roi = RectROI([100, 100], [150, 150], pen='r')
        self.view.addItem(self.roi)

        self.roi_win.show()


        self._widget.recordBinaryMaskButton.clicked.disconnect(self.initiateBinaryMask)
        self._widget.recordBinaryMaskButton.clicked.connect(self.saveBinaryMask)
        self._widget.recordBinaryMaskButton.setText('Save and load')

    def saveBinaryMask(self):

        img_shape = self.latest_image.shape
        mask = np.zeros(img_shape, dtype=np.uint8)

        x, y = map(int, self.roi.pos())
        w, h = map(int, self.roi.size())

        x = max(0, x)
        y = max(0, y)
        x_end = min(x + w, img_shape[1])
        y_end = min(y + h, img_shape[0])

        mask[y:y_end, x:x_end] = 1
        self.__binary_mask = mask

        filePath = guitools.askForFilePath(self._widget, 'Save and load binary mask', _binaryMask, isSaving=True)
        if filePath:
            np.save(filePath, mask)

        self.roi_win.close()
        self._widget.recordBinaryMaskButton.clicked.disconnect(self.saveBinaryMask)
        self._widget.recordBinaryMaskButton.clicked.connect(self.initiateBinaryMask)
        self._widget.recordBinaryMaskButton.setText('Record binary mask')

    def loadBinaryMask(self):

        filePath = guitools.askForFilePath(self._widget, 'Load binary mask', _binaryMask)
        if filePath:
            self.__binary_mask = np.load(filePath)

    def clearBinaryMask(self):

        self.__binary_mask = None

    def showBinaryMask(self):


        mask = self.__binary_mask
        if mask is None:
            QMessageBox.information(self._widget, "Avertissement", "No binary mask loaded.")
            return


        detectorFastIdx = self._widget.fastImgDetectorsPar.currentIndex()
        self.detectorFast = self._widget.fastImgDetectors[detectorFastIdx]
        self.detectorFast_controller = self._master.detectorsManager._subManagers[self.detectorFast]

        time.sleep(1)
        img = self.detectorFast_controller.getLatestFrame()
        # import tifffile as tf
        # path = "//storage3.ad.scilifelab.se/testalab/Abigail/Data_Calcium_15_05_2025/Calcium7/"
        # file = "Timelapse_40Frames_15s_noFilter_snap_WidefieldCamera_"
        # img = tf.imread(path + file + str(29) + ".tiff")

        self.roi_win = pg.GraphicsLayoutWidget(title="Actual Binary Mask")
        self.view = self.roi_win.addViewBox()
        self.view.setAspectLocked(True)

        img_item = pg.ImageItem(img)
        self.view.addItem(img_item)

        # Créer l’overlay rouge transparent basé sur le masque
        overlay = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
        overlay[..., 0] = 255  # rouge
        overlay[..., 3] = (mask * 120).astype(np.uint8)  # transparence

        overlay_item = pg.ImageItem(overlay)
        self.view.addItem(overlay_item)

        self.roi_win.show()


class RunMode(enum.Enum):
    Experiment = 1
    Visualize = 2
    Validate = 3




