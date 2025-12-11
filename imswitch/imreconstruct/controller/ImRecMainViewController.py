import copy
import os
import cupy as cp
from cupyx.scipy.ndimage import affine_transform
import h5py
import numpy as np
import tifffile as tiff

import imswitch.imreconstruct.view.guitools as guitools
from imswitch.imcommon.controller import PickDatasetsController
from imswitch.imreconstruct.model import DataObj, ReconObj, Reconstructor
from .DataFrameController import DataFrameController
from .MultiDataFrameController import MultiDataFrameController
from .ReconstructionViewController import ReconstructionViewController
from .ScanParamsController import ScanParamsController
from .basecontrollers import ImRecWidgetController


class ImRecMainViewController(ImRecWidgetController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dataFrameController = self._factory.createController(
            DataFrameController, self._widget.dataFrame
        )
        self.multiDataFrameController = self._factory.createController(
            MultiDataFrameController, self._widget.multiDataFrame
        )
        self.reconstructionController = self._factory.createController(
            ReconstructionViewController, self._widget.reconstructionWidget
        )
        self.pickDatasetsController = self._factory.createController(
            PickDatasetsController, self._widget.pickDatasetsDialog
        )

        self._reconstructor = Reconstructor()

        self._currentDataObj = None
        self._dataFolder = None
        self._saveFolder = None

        self._commChannel.sigDataFolderChanged.connect(self.dataFolderChanged)
        self._commChannel.sigSaveFolderChanged.connect(self.saveFolderChanged)
        self._commChannel.sigCurrentDataChanged.connect(self.currentDataChanged)
        self._commChannel.sigNewDataAddedFromModule.connect(self.newDataFromModule)

        self._widget.sigSaveReconstruction.connect(lambda: self.saveCurrent('reconstruction'))
        self._widget.sigSaveReconstructionAll.connect(lambda: self.saveAll('reconstruction'))
        self._widget.sigSaveCoeffs.connect(lambda: self.saveCurrent('coefficients'))
        self._widget.sigSaveCoeffsAll.connect(lambda: self.saveAll('coefficients'))
        self._widget.sigSetDataFolder.connect(self.setDataFolder)
        self._widget.sigSetSaveFolder.connect(self.setSaveFolder)

        self._widget.parTree.p.param('Acquisition parameters').sigTreeStateChanged.connect(self.acquisitionParsChanged)

        self._widget.sigReconstuctCurrent.connect(self.reconstructCurrent)
        self._widget.sigReconstuctMulti.connect(self.reconstructMultiColor)
        self._widget.sigReconstructMultiConsolidated.connect(
            lambda: self.reconstructMulti(consolidate=True)
        )
        self._widget.sigReconstructMultiIndividual.connect(
            lambda: self.reconstructMulti(consolidate=False)
        )
        self._widget.sigQuickLoadData.connect(self.quickLoadData)
        self._widget.sigUpdate.connect(lambda: self.updateScanParams(applyOnCurrentRecon=True))

        self.acquisitionParsChanged()
    def acquisitionParsChanged(self):
        cycles = self._widget.getCycles()
        planes_in_cycle = self._widget.getPlanesInCycle()
        self._commChannel.sigDataStackingChanged.emit(cycles, planes_in_cycle)
    def dataFolderChanged(self, dataFolder):
        self._dataFolder = dataFolder

    def saveFolderChanged(self, saveFolder):
        self._saveFolder = saveFolder

    def setDataFolder(self):
        dataFolder = guitools.askForFolderPath(self._widget)
        if dataFolder:
            self._commChannel.sigDataFolderChanged.emit(dataFolder)

    def setSaveFolder(self):
        saveFolder = guitools.askForFolderPath(self._widget)
        if saveFolder:
            self._commChannel.sigSaveFolderChanged.emit(saveFolder)

    def quickLoadData(self):
        dataPath = guitools.askForFilePath(self._widget, defaultFolder=self._dataFolder)
        if dataPath:
            self._logger.debug(f'Loading data at: {dataPath}')

            datasetsInFile = DataObj.getDatasetNames(dataPath)
            datasetToLoad = None
            if len(datasetsInFile) < 1:
                # File does not contain any datasets
                return
            elif len(datasetsInFile) > 1:
                # File contains multiple datasets
                self.pickDatasetsController.setDatasets(dataPath, datasetsInFile)
                if not self._widget.showPickDatasetsDialog(blocking=True):
                    return

                datasetsSelected = self.pickDatasetsController.getSelectedDatasets()
                if len(datasetsSelected) < 1:
                    # No datasets selected
                    return
                elif len(datasetsSelected) == 1:
                    datasetToLoad = datasetsSelected[0]
                else:
                    # Load into multi-data list
                    for datasetName in datasetsSelected:
                        self._commChannel.sigAddToMultiData.emit(dataPath, datasetName)
                    self._widget.raiseMultiDataDock()
                    return

            name = os.path.split(dataPath)[1]
            if self._currentDataObj is not None:
                self._currentDataObj.checkAndUnloadData()
            self._currentDataObj = DataObj(name, None, path=dataPath)
            self._currentDataObj.checkAndLoadData()
            if self._currentDataObj.dataLoaded:
                self._commChannel.sigCurrentDataChanged.emit(self._currentDataObj)
                self._logger.debug('Data loaded')
                self._widget.raiseCurrentDataDock()
            else:
                pass

    def newDataFromModule(self):
        if self._widget.getAutoReconstructNewDataBool():
            self.reconstructCurrent()

    def currentDataChanged(self, dataObj):
        self._currentDataObj = dataObj
        """Could be used in future to set recon parameters from dataAttr"""
        # Update scan params based on new data
        # TODO: What if the attribute names change in imcontrol?
        # try:
        #     stepSizesAttr = dataObj.attrs['ScanStage:axis_step_size']
        # except KeyError:
        #     pass
        # else:
        #     for i in range(0, min(4, len(stepSizesAttr))):
        #         self._scanParDict['step_sizes'][i] = str(stepSizesAttr[i] * 1000)  # convert um->nm
        #
        # self.updateScanParams()

    def reconstructCurrent(self):
        if self._currentDataObj is None:
            return

        self.reconstruct([self._currentDataObj], consolidate=False)

    def apply_affine_gpu_batch(self, stack, M):
        stack_gpu = cp.array(stack, dtype=cp.float32)

        matrix = cp.array([[M[0, 0], M[0, 1]],
                           [M[1, 0], M[1, 1]]])
        offset = cp.array([M[1, 2], M[0, 2]])
        Minv = cp.linalg.inv(matrix.T)
        offset_sci = -Minv @ offset

        out_gpu = cp.zeros_like(stack_gpu)

        # Batch GPU processing (loop is cheap on GPU)
        for i in range(stack_gpu.shape[0]):
            out_gpu[i] = affine_transform(stack_gpu[i], Minv, offset=offset_sci, order=1)

        return cp.asnumpy(out_gpu).astype(np.uint16)

    def crop_and_rotate_gpu(self, chunk_size=400):
        if self._currentDataObj is None:
            return

        datapath = self._currentDataObj.dataPath
        folder = os.path.dirname(datapath)
        typef = '.hdf5'

        ROI_file = os.path.join(folder, 'ROI.txt')
        Transform_file = os.path.join(folder, 'Transform.txt')

        ROI = np.loadtxt(ROI_file, dtype=int)
        T = np.loadtxt(Transform_file, dtype=float)

        # Output files
        temp_files = {
            "green": os.path.join(folder, "crop_green" + typef),
            "red": os.path.join(folder, "crop_red" + typef),
            "orange": os.path.join(folder, "crop_orange" + typef)
        }
        # Open input file once, create output files once
        with h5py.File(datapath, "r") as infile, \
                h5py.File(temp_files["green"], "w") as gfile, \
                h5py.File(temp_files["red"], "w") as rfile, \
                h5py.File(temp_files["orange"], "w") as ofile:

            dset = infile["Orca"]
            nframes, H, W = dset.shape

            # compute output shapes
            H_or, W_or = ROI[0, 1] - ROI[0, 0], ROI[1, 1] - ROI[1, 0]
            H_gr, W_gr = ROI[2, 1] - ROI[2, 0], ROI[3, 1] - ROI[3, 0]
            H_rd, W_rd = ROI[4, 1] - ROI[4, 0], ROI[5, 1] - ROI[5, 0]

            # create output datasets
            g_out = gfile.create_dataset("Orca", (nframes, H_gr, W_gr), dtype=np.uint16)
            r_out = rfile.create_dataset("Orca", (nframes, H_rd, W_rd), dtype=np.uint16)
            o_out = ofile.create_dataset("Orca", (nframes, H_or, W_or), dtype=np.uint16)

            # Prepare transform matrices
            greenT = T[0:2, :]
            redT = T[2:4, :]

            # ---- CHUNKED PROCESSING ----
            for start in range(0, nframes, chunk_size):
                end = min(start + chunk_size, nframes)

                # Load only this chunk
                chunk = dset[start:end]  # shape (chunk, H, W)

                # ---- ORANGE (no transform) ----
                orange = chunk[:, ROI[0, 0]:ROI[0, 1], ROI[1, 0]:ROI[1, 1]]
                o_out[start:end] = orange.astype(np.uint16)

                # ---- GREEN ----
                green = chunk[:, ROI[2, 0]:ROI[2, 1], ROI[3, 0]:ROI[3, 1]]
                greenT_out = self.apply_affine_gpu_batch(green, greenT)
                g_out[start:end] = greenT_out

                # ---- RED ----
                red = chunk[:, ROI[4, 0]:ROI[4, 1], ROI[5, 0]:ROI[5, 1]]
                redT_out = self.apply_affine_gpu_batch(red, redT)
                r_out[start:end] = redT_out

                print(f"Processed frames {start} → {end} / {nframes}")

        return temp_files

        # with h5py.File(datapath, 'r') as datafile:
        #     data = np.array(datafile['Orca'][:])
        #     print(f"Original data shape: {data.shape}")
        #
        # # Crop each channel
        # data_orange = data[:, ROI_params[0, 0]:ROI_params[0, 1], ROI_params[1, 0]:ROI_params[1, 1]]
        # data_green = data[:, ROI_params[2, 0]:ROI_params[2, 1], ROI_params[3, 0]:ROI_params[3, 1]]
        # data_red = data[:, ROI_params[4, 0]:ROI_params[4, 1], ROI_params[5, 0]:ROI_params[5, 1]]
        #
        # # Apply GPU affine transform
        # # def apply_affine_gpu(stack, M):
        # #     stack_gpu = cp.array(stack, dtype=cp.float32)
        # #     matrix = cp.array([[M[0, 0], M[0, 1]], [M[1, 0], M[1, 1]]])
        # #     offset = cp.array([M[1, 2], M[0, 2]])
        # #     Minv = cp.linalg.inv(matrix.T)
        # #     offset_for_scipy = -Minv @ offset
        # #     out_gpu = cp.zeros_like(stack_gpu)
        # #     for i in range(stack_gpu.shape[0]):
        # #         out_gpu[i] = affine_transform(stack_gpu[i], Minv, offset=offset_for_scipy, order=1)
        # #
        # #     return cp.asnumpy(out_gpu)
        #
        #
        #
        # # Transform green channel
        # greenT = T[0:2, :]
        # green_transformed = apply_affine_gpu(data_green, greenT)
        # green_transformed = green_transformed.astype(np.uint16)
        #
        # # Transform red channel
        # redT = T[2:4, :]
        # red_transformed = apply_affine_gpu(data_red, redT)
        # red_transformed = red_transformed.astype(np.uint16)
        #
        # # Orange channel does not need transform
        # orange_transformed = data_orange
        #
        # # Save temporary HDF5 files for DataObj
        # temp_files = {
        #     'green': os.path.join(folder, 'crop_green' + typef),
        #     'red': os.path.join(folder, 'crop_red' + typef),
        #     'orange': os.path.join(folder, 'crop_orange' + typef)
        # }
        #
        # for name, arr in zip(['green', 'red', 'orange'],
        #                      [green_transformed, red_transformed, orange_transformed]):
        #     with h5py.File(temp_files[name], 'w') as f:
        #         f.create_dataset('Orca', data=arr)
        #
        # return temp_files

    # def crop_and_rotate_fast(self):
    #     import h5py
    #     import numpy as np
    #     #from scipy.ndimage import affine_transform
    #     from cupyx.scipy.ndimage import affine_transform
    #
    #     datapath = self._currentDataObj.dataPath
    #     folder = os.path.dirname(datapath)
    #
    #     # Load ROI + transform files once
    #     ROI = np.loadtxt(folder + '/ROI.txt', dtype=int)
    #     T = np.loadtxt(folder + '/Transform.txt', dtype=float)
    #
    #     with h5py.File(datapath, 'r') as f:
    #         data = f['Orca'][()]  # Loads once
    #
    #     # -------------------------
    #     # Crops
    #     # -------------------------
    #     orange = data[:, ROI[0, 0]:ROI[0, 1], ROI[1, 0]:ROI[1, 1]]
    #     green = data[:, ROI[2, 0]:ROI[2, 1], ROI[3, 0]:ROI[3, 1]]
    #     red = data[:, ROI[4, 0]:ROI[4, 1], ROI[5, 0]:ROI[5, 1]]
    #
    #     # -------------------------
    #     # Apply affine transforms in batch, not per frame
    #     # -------------------------
    #
    #     def apply_affine_gpu(stack, T):
    #         # stack: Z, Y, X (NumPy array)
    #         stack_gpu = cp.array(stack)  # move to GPU
    #
    #         M = cp.array([[T[0, 0], T[0, 1]], [T[1, 0], T[1, 1]]])
    #         offset = cp.array([T[1, 2], T[0, 2]])
    #         Minv = cp.linalg.inv(M.T)
    #         offset_for_scipy = -Minv @ offset
    #
    #         # Output array on GPU
    #         out_gpu = cp.zeros_like(stack_gpu)
    #
    #         # Apply affine transform to all slices (still loop, but on GPU)
    #         for i in range(stack_gpu.shape[0]):
    #             out_gpu[i] = affine_transform(stack_gpu[i], Minv, offset=offset_for_scipy, order=1)
    #
    #         return cp.asnumpy(out_gpu)  # back to CPU
    #
    #     def apply_original_affine(stack, T):
    #         """
    #         stack: (N, H, W)
    #         T: 2×3 matrix from Transform_file (two rows)
    #         """
    #
    #         import numpy as np
    #         from scipy.ndimage import affine_transform
    #
    #         # Extract same as your original code
    #         M = np.array([[T[0, 0], T[0, 1]],
    #                       [T[1, 0], T[1, 1]]])
    #
    #         # Note: Your original code uses swapped order here:
    #         # offset = [ty, tx]
    #         offset = np.array([T[1, 2], T[0, 2]])
    #
    #         # Your original inversion step
    #         Minv = np.linalg.inv(M.T)
    #
    #         # Original offset mapping
    #         sci_offset = -Minv @ offset
    #
    #         out = np.zeros_like(stack)
    #         for i in range(stack.shape[0]):
    #             out[i] = affine_transform(
    #                 stack[i],
    #                 matrix=Minv,
    #                 offset=sci_offset,
    #                 order=1,
    #                 mode='constant'
    #             )
    #         return out
    #
    #     greenT = apply_affine_gpu(green, T[0:2, :])
    #     redT = apply_affine_gpu(red, T[2:4, :])
    #     # orange stays unchanged
    #
    #     # -------------------------
    #     # Save results once
    #     # -------------------------
    #     typef = '.hdf5'
    #     with h5py.File(datapath + 'crop_green' + typef, 'w') as f: f['Orca'] = greenT
    #     with h5py.File(datapath + 'crop_red' + typef, 'w') as f: f['Orca'] = redT
    #     with h5py.File(datapath + 'crop_orange' + typef, 'w') as f: f['Orca'] = orange
    #

    def quickLoadDatafromFile(self, dataPath):

            self._logger.debug(f'Loading data at: {dataPath}')

            datasetsInFile = DataObj.getDatasetNames(dataPath)
            datasetToLoad = None
            if len(datasetsInFile) < 1:
                # File does not contain any datasets
                return
            elif len(datasetsInFile) > 1:
                # File contains multiple datasets
                self.pickDatasetsController.setDatasets(dataPath, datasetsInFile)
                if not self._widget.showPickDatasetsDialog(blocking=True):
                    return

                datasetsSelected = self.pickDatasetsController.getSelectedDatasets()
                if len(datasetsSelected) < 1:
                    # No datasets selected
                    return
                elif len(datasetsSelected) == 1:
                    datasetToLoad = datasetsSelected[0]
                else:
                    # Load into multi-data list
                    for datasetName in datasetsSelected:
                        self._commChannel.sigAddToMultiData.emit(dataPath, datasetName)
                    self._widget.raiseMultiDataDock()
                    return

            name = os.path.split(dataPath)[1]
            dataobj = DataObj(name, None, path=dataPath)
            dataobj.checkAndLoadData()
            if dataobj.dataLoaded:
                self._logger.debug('Data from file loaded')
                return dataobj
            else:
                pass
    # def reconstructMultiColor(self):
    #     path = 'D:/SnoutyData/2025-10-08/'
    #     typef = '.hdf5'
    #     datapath = self._currentDataObj.dataPath
    #
    #     self.crop_and_rotate()
    #
    #
    #     data = [self.quickLoadDatafromFile(datapath + 'crop_green' + typef),self.quickLoadDatafromFile(datapath + 'crop_red' + typef),self.quickLoadDatafromFile(datapath + 'crop_orange' + typef)]
    #
    #     self.reconstruct(data, consolidate=False)
    # def reconstructMultiColor(self):
    #     typef = '.hdf5'
    #     datapath = self._currentDataObj.dataPath
    #
    #     # -----------------------
    #     # 1. Perform crop + rotate only once
    #     # -----------------------
    #     self.crop_and_rotate_fast()  # <-- replaced version, see below
    #
    #     # -----------------------
    #     # 2. Load 3 color stacks in one shot
    #     # -----------------------
    #     green = self.quickLoadDatafromFile(datapath + 'crop_green' + typef)
    #     red = self.quickLoadDatafromFile(datapath + 'crop_red' + typef)
    #     orange = self.quickLoadDatafromFile(datapath + 'crop_orange' + typef)
    #
    #     # -----------------------
    #     # 3. Run reconstruction once for all 3
    #     # -----------------------
    #     self.reconstruct([green, red, orange], consolidate=False)
    def reconstructMultiColor(self):
        temp_files = self.crop_and_rotate_gpu()

        green_obj = DataObj('green', None, path=temp_files['green'])
        red_obj = DataObj('red', None, path=temp_files['red'])
        orange_obj = DataObj('orange', None, path=temp_files['orange'])

        for obj in [green_obj, red_obj, orange_obj]:
            obj.checkAndLoadData()

        self.reconstruct([green_obj, red_obj, orange_obj], consolidate=False)

        # Unload before deleting temp files
        for obj in [green_obj, red_obj, orange_obj]:
            obj.checkAndUnloadData()

        # Now safe to delete
        for f in temp_files.values():
            if os.path.exists(f):
                os.remove(f)

    def reconstructMulti(self, consolidate):
        self.reconstruct(self._widget.getMultiDatas(), consolidate)

    def reconstruct(self, dataObjs, consolidate, get_Item=False):
        #consolidate not fully implemented now
        reconObj = None
        for index, dataObj in enumerate(dataObjs):
            preloaded = dataObj.dataLoaded
            try:
                dataObj.checkAndLoadData()

                if not consolidate or index == 0:
                    reconObj = ReconObj(dataObj.name,
                                        self._widget.timepoints_text)

                data = dataObj.data
                if self._widget.getBleachCorrectionBool():
                    data = self.bleachingCorrection(data)

                timepoints = self._widget.getTimepoints()
                if timepoints > 1 and self._widget.getAverageTimepointsBool():
                    shape = data.shape
                    reshaped = np.reshape(data, (timepoints, shape[0]//timepoints, shape[1], shape[2]))
                    data = np.mean(reshaped, axis=0)
                    timepoints = 1

                cycles = self._widget.getCycles()
                planes_in_cycle = self._widget.getPlanesInCycle()
                dataShape_tp = np.array([cycles*planes_in_cycle, data.shape[1], data.shape[2]])
                reconstructionSize = self._reconstructor.getReconstructionSize(dataShape_tp, self._widget.getPixelSizeNm(),
                                                                             self._widget.getSkewAngleRad(),
                                                                             self._widget.getDeltaY(),
                                                                             self._widget.getReconstructionVxSize())

                reconObj.allocateReconstruction(timepoints, reconstructionSize)

                for tp in range(timepoints):
                    """Restack data"""
                    slices = cycles * planes_in_cycle
                    tp_data = data[tp*slices:(tp + 1)*slices]
                    if self._widget.getRestackBool():
                        try:
                            restacked = np.zeros_like(tp_data)
                            for i in range(planes_in_cycle):
                                restacked[i * cycles:(i + 1) * cycles] = tp_data[i::planes_in_cycle]
                        except ValueError:
                            self._logger.warning('Data shape does not match given restacking parameters')
                    else:
                        restacked = tp_data
                    if self._widget.getPosScanDirection():
                        restacked = np.flip(restacked, 0)
                    self._logger.debug('Reconstructing data tp: %s' % tp)
                    recon = self._reconstructor.simpleDeskew(restacked, self._widget.getPixelSizeNm(),
                                                             self._widget.getSkewAngleRad(),
                                                             self._widget.getDeltaY(),
                                                             self._widget.getReconstructionVxSize())
                    reconObj.addReconstructionTimepoint(tp, recon)

            finally:
                if not preloaded:
                    dataObj.checkAndUnloadData()

            if not consolidate:
                if get_Item :
                    item=self._widget.addNewReconstruction(reconObj, reconObj.name, get_Item=True)
                    return item
                else:
                    item = self._widget.addNewReconstruction(reconObj, reconObj.name)


        if consolidate:
            self._widget.addNewReconstruction(reconObj, f'{reconObj.name}_multi')

    def reconstruct_multicolor(self, dataObjs, consolidate):
        #consolidate not fully implemented now
        reconObj = None
        for index, dataObj in enumerate(dataObjs):
            preloaded = dataObj.dataLoaded
            try:
                dataObj.checkAndLoadData()

                if not consolidate or index == 0:
                    reconObj = ReconObj(dataObj.name,
                                        self._widget.timepoints_text)

                data = dataObj.data
                if self._widget.getBleachCorrectionBool():
                    data = self.bleachingCorrection(data)


                timepoints = self._widget.getTimepoints()
                if timepoints > 1 and self._widget.getAverageTimepointsBool():
                    shape = data.shape
                    reshaped = np.reshape(data, (timepoints, shape[0]//timepoints, shape[1], shape[2]))
                    data = np.mean(reshaped, axis=0)
                    timepoints = 1

                split_data = np.split(data, 3,axis =0)
                split_objs = []
                for i, part in enumerate(split_data):
                    split_obj = DataObj(f"{dataObj.name}_split{i + 1}", dataObj.dataset, path=dataObj.path)
                    split_obj.data = part
                    split_obj.dataLoaded = True
                    split_objs.append(split_obj)

                colors = ['green', 'yellow', 'red']
                for split_obj, color in zip(data, colors):
                    reconObj = ReconObj(split_obj.name, self._widget.timepoints_text)
                    split_part = split_obj.data

                    cycles = self._widget.getCycles()
                    planes_in_cycle = self._widget.getPlanesInCycle()
                    dataShape_tp = np.array([cycles*planes_in_cycle, data.shape[1], data.shape[2]])
                    reconstructionSize = self._reconstructor.getReconstructionSize(dataShape_tp, self._widget.getPixelSizeNm(),
                                                                             self._widget.getSkewAngleRad(),
                                                                             self._widget.getDeltaY(),
                                                                             self._widget.getReconstructionVxSize())

                    reconObj.allocateReconstruction(timepoints, reconstructionSize)

                    for tp in range(timepoints):
                        """Restack data"""
                        slices = cycles * planes_in_cycle
                        tp_data = data[tp*slices:(tp + 1)*slices]
                        if self._widget.getRestackBool():
                            try:
                                restacked = np.zeros_like(tp_data)
                                for i in range(planes_in_cycle):
                                    restacked[i * cycles:(i + 1) * cycles] = tp_data[i::planes_in_cycle]
                            except ValueError:
                                self._logger.warning('Data shape does not match given restacking parameters')
                        else:
                            restacked = tp_data
                        if self._widget.getPosScanDirection():
                            restacked = np.flip(restacked, 0)
                            self._logger.debug('Reconstructing data tp: %s' % tp)
                        recon = self._reconstructor.simpleDeskew(restacked, self._widget.getPixelSizeNm(),
                                                             self._widget.getSkewAngleRad(),
                                                             self._widget.getDeltaY(),
                                                             self._widget.getReconstructionVxSize())
                        reconObj.addReconstructionTimepoint(tp, recon)
                    self._widget.addNewReconstruction(reconObj, f"{reconObj.name}_{color}")


            finally:
                    if not preloaded:
                        dataObj.checkAndUnloadData()
            if not consolidate:
                self._widget.addNewReconstruction(reconObj, reconObj.name)

        if consolidate:
            self._widget.addNewReconstruction(reconObj, f'{reconObj.name}_multi')

    def bleachingCorrection(self, data):
        correctedData = data.copy()
        energy = np.sum(data, axis=(1, 2))
        for i in range(data.shape[0]):
            c = (energy[0] / energy[i]) ** 4
            correctedData[i, :, :] = data[i, :, :] * c
        return correctedData

    def saveCurrent(self, dataType):
        """ Saves the reconstructed image or coefficeints from the current
        ReconObj to a user-specified destination. """

        filePath = guitools.askForFilePath(self._widget,
                                           caption=f'Save {dataType}',
                                           defaultFolder=self._saveFolder or self._dataFolder,
                                           nameFilter='*.tiff', isSaving=True)

        if filePath:
            reconObj = self.reconstructionController.getActiveReconObj()
            if dataType == 'reconstruction':
                self.saveReconstruction(reconObj, filePath)
            elif dataType == 'coefficients':
                self.saveCoefficients(reconObj, filePath)
            else:
                raise ValueError(f'Invalid save data type "{dataType}"')

    def saveAll(self, dataType):
        """ Saves the reconstructed image or coefficeints from all available
        ReconObj objects to a user-specified directory. """

        dirPath = guitools.askForFolderPath(self._widget,
                                            caption=f'Save all {dataType}',
                                            defaultFolder=self._saveFolder or self._dataFolder)

        if dirPath:
            for name, reconObj in self.reconstructionController.getAllReconObjs():
                # Avoid overwriting
                filePath = os.path.join(dirPath, f'{name}.{dataType}.tiff')
                filePathNew = filePath
                numExisting = 0
                while os.path.exists(filePathNew):
                    numExisting += 1
                    pathWithoutExt, pathExt = os.path.splitext(filePath)
                    filePathNew = f'{pathWithoutExt}_{numExisting}{pathExt}'
                filePath = filePathNew

                # Save
                if dataType == 'reconstruction':
                    self.saveReconstruction(reconObj, filePath)
                elif dataType == 'coefficients':
                    self.saveCoefficients(reconObj, filePath)
                else:
                    raise ValueError(f'Invalid save data type "{dataType}"')

    def saveReconstruction(self, reconObj, filePath):
        # scanParDict = reconObj.getScanParams()
        # vxsizec = int(float(
        #     scanParDict['step_sizes'][scanParDict['dimensions'].index(
        #         self._widget.r_l_text
        #     )]
        # ))
        # vxsizer = int(float(
        #     scanParDict['step_sizes'][scanParDict['dimensions'].index(
        #         self._widget.u_d_text
        #     )]
        # ))
        # vxsizez = int(float(
        #     reconObj.scanParDict['step_sizes'][scanParDict['dimensions'].index(
        #         self._widget.b_f_text
        #     )]
        # ))
        # dt = int(float(
        #     scanParDict['step_sizes'][scanParDict['dimensions'].index(
        #         self._widget.timepoints_text
        #     )]
        # ))

        self._logger.debug(f'Trying to save to: {filePath}, Vx size: {self._widget.getReconstructionVxSize(), self._widget.getReconstructionVxSize(), self._widget.getReconstructionVxSize()},'
                           f' dt: -')
        # Reconstructed image
        reconstrData = reconObj.getReconstruction() #Not good for memory limitations
        reconstrData = np.array([reconstrData])
        reconstrData = np.swapaxes(reconstrData, 1, 2)
        tiff.imwrite(filePath, reconstrData,
                     imagej=True, resolution=(1 / self._widget.getReconstructionVxSize(), 1 / self._widget.getReconstructionVxSize()),
                     metadata={'spacing': self._widget.getReconstructionVxSize(), 'unit': 'nm', 'axes': 'TZCYX'})
        """Reshape back to original, since we do not deep copy from reconObj"""
        reconstrData = np.swapaxes(reconstrData, 1, 2)
        reconstrData = reconstrData[0]
    def saveCoefficients(self, reconObj, filePath):
        coeffs = copy.deepcopy(reconObj.getCoeffs())
        self._logger.debug(f'Shape of coeffs: {coeffs.shape}')
        coeffs = np.swapaxes(coeffs, 1, 2)
        tiff.imwrite(filePath, coeffs,
                     imagej=True, resolution=(1, 1),
                     metadata={'spacing': 1, 'unit': 'px', 'axes': 'TZCYX'})


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
