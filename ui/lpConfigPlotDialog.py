import os.path

from qgis.PyQt.QtWidgets import QDialog, QColorDialog, QMessageBox
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QTimer

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'lpConfigPlotDialog.ui'))


class LPConfigPlotDialog(QDialog, FORM_CLASS):

    def __init__(self, iface, model, index):
        super(LPConfigPlotDialog, self).__init__(None)
        self.iface = iface
        self.setupUi(self)
        self.model = model
        self.index = index
        self.data = {}
        self.row = self.model.itemFromIndex(self.index).row()
        self.configs = self.model.getConfigs(self.row)

        self.plotColor.clicked.connect(self.changePlotColor)

        self.setParams()

        self.CBX_Data.currentTextChanged.connect(self.changeDataName)
        self.CKB_MovAve.stateChanged.connect(self.changeMovAveState)
        self.SPN_MovAveN.valueChanged.connect(self.changeMovAveN)
        self.CKB_FullRes.stateChanged.connect(self.changeFullResState)
        self.SPN_MaxDist.valueChanged.connect(self.handle_changeMaxDist)
        self.CKB_SamplingState.stateChanged.connect(self.handle_changeAreaSamplingState)
        self.SPN_SamplingWidth.valueChanged.connect(self.changeAreaSamplingWidth)
        self.BTN_Remove.clicked.connect(self.removeData)
        self.GRP_Main.clicked.connect(self.changeVisibleState)

        self.timer_area_sampling_spin_box = QTimer()
        self.timer_area_sampling_spin_box.setSingleShot(True)
        self.timer_area_sampling_spin_box.timeout.connect(self.changeAreaSamplingState)

        self.timer_max_distance_tieline_spin_box = QTimer()
        self.timer_max_distance_tieline_spin_box.setSingleShot(True)
        self.timer_max_distance_tieline_spin_box.timeout.connect(self.changeMaxDist)

        self.TXT_PlotLabel.textChanged.connect(self.handle_updatePlotLabel)
        self.timer_plot_label = QTimer()
        self.timer_plot_label.setSingleShot(True)
        self.timer_plot_label.timeout.connect(self.updatePlotLabel)

    def setBGColor(self, target, color):
        target.setStyleSheet("background-color: %s" % color.name())

    def changeVisibleState(self, state):
        self.model.setCheckState(self.row, int(state) * 2)

    def changePlotColor(self):
        curColor = self.model.getColor(self.row)
        newColor = QColorDialog().getColor(curColor)
        if newColor.isValid() and newColor.name() is not curColor.name():
            self.model.setColor(self.row, newColor)
            self.setBGColor(self.plotColor, newColor)

    def changeDataName(self, selectedText):
        self.model.setDataName(self.row, selectedText)
        self.TXT_PlotLabel.setText(selectedText)

    def changeMovAveState(self, state):
        self.model.setConfigs(self.row, {'movingAverage': state})

    def changeMovAveN(self):
        self.model.setConfigs(self.row,
                              {'movingAverageN': self.SPN_MovAveN.value()})

    def changeFullResState(self, state):
        self.model.setConfigs(self.row, {'fullRes': state})

    def handle_changeAreaSamplingState(self, state):
        self.timer_area_sampling_spin_box.start(500)

    def changeAreaSamplingState(self):
        state = self.CKB_SamplingState.checkState()
        self.model.setConfigs(self.row, {'areaSampling': state})

    def changeAreaSamplingWidth(self):
        self.model.setConfigs(
            self.row, {'areaSamplingWidth': self.SPN_SamplingWidth.value()})

    def handle_changeMaxDist(self):
        self.timer_max_distance_tieline_spin_box.start(500)

    def changeMaxDist(self):
        sameLayers = self.model.findSameLayers(self.model.getLayerId(self.row))
        config = {'maxDistance': self.SPN_MaxDist.value()}
        [self.model.setConfigs(r, config) for r in sameLayers]

    def setParams(self):
        r = self.row
        # set layer name with layer type
        layerName = self.model.getLayer(r)
        layerType = self.model.getLayerTypeName(r)

        # set groupbox title
        self.GPB_LayerInfo.setTitle(f'{layerName} ({layerType})')

        # set plot label
        dataName = self.model.getDataName(r)
        if 'label' in self.configs['plotOptions']:
            label = self.configs['plotOptions']['label']
        else:
            label = dataName
        self.TXT_PlotLabel.setText(label)

        # set display state
        self.GRP_Main.setChecked(self.model.getCheckState(r))

        # set plot color
        self.setBGColor(self.plotColor, self.model.getColor(r))

        # set data name and list
        self.setComboBoxItems(self.CBX_Data, self.model.getLayerId(r))

        # set moving average
        # config = self.model.getConfigs(r)
        self.CKB_MovAve.setCheckState(self.configs['movingAverage'])
        self.SPN_MovAveN.setValue(self.configs['movingAverageN'])
        # set full resolution
        self.CKB_FullRes.setCheckState(self.configs['fullRes'])

        # set sampling area
        self.CKB_SamplingState.setCheckState(self.configs['areaSampling'])
        self.SPN_SamplingWidth.setValue(self.configs['areaSamplingWidth'])

        # set max distance
        self.SPN_MaxDist.setValue(self.configs['maxDistance'])

        # Vector vs. Raster
        if self.model.getLayerType(r):  # Raster
            self.GRP_Raster.setEnabled(True)
            self.GRP_Vector.setEnabled(False)
            self.CKB_MovAve.setEnabled(True)
            self.SPN_MovAveN.setEnabled(True)
            self.CKB_SamplingState.setEnabled(True)
            self.SPN_SamplingWidth.setEnabled(True)
            self.SPN_MaxDist.setEnabled(False)
        else:  # Vector
            self.GRP_Raster.setEnabled(False)
            self.GRP_Vector.setEnabled(True)
            self.CKB_MovAve.setEnabled(False)
            self.SPN_MovAveN.setEnabled(False)
            self.SPN_MaxDist.setEnabled(True)
            self.CKB_SamplingState.setEnabled(False)
            self.SPN_SamplingWidth.setEnabled(False)

    def handle_updatePlotLabel(self):
        self.timer_plot_label.start(1000)

    def updatePlotLabel(self):
        label = self.TXT_PlotLabel.text()
        self.model.setPlotLabel(self.row, label)

    def setComboBoxItems(self, cmbBox, layerId):
        layers = self.iface.mapCanvas().layers()
        if len(layers) == 0:
            return
        layer = [l for l in layers if l.id() == layerId][0]
        currentData = self.model.getDataName(self.row)
        if layer.type() == layer.RasterLayer:  # Raster Layer
            [cmbBox.addItem('Band ' + str(i + 1)) for i in range(layer.bandCount())]
        elif layer.type() == layer.VectorLayer:  # Vector Layer
            fields = layer.dataProvider().fields()
            myList = [f.name() for f in fields if f.type() == 2 or f.type() == 6]
            cmbBox.addItems(myList)
        else:
            return False

        return cmbBox.setCurrentIndex(cmbBox.findText(currentData))

    def removeData(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setText("Are you sure to remove this data?")
        msgBox.setWindowTitle("Remove Data")
        buttons = QMessageBox.Ok | QMessageBox.Cancel
        msgBox.setStandardButtons(buttons)
        returnValue = msgBox.exec_()
        if returnValue == QMessageBox.Ok:
            self.model.removeRows(self.row, 1)
            self.close()

    def accept(self):
        self.close()
