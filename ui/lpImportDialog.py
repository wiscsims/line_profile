# -*- coding: utf-8 -*-
# from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.PyQt import uic
from qgis.core import QgsProject
# from qgis.gui import QgisInterface

import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'lpImportDialog.ui'))


class LPImportDialog(QDialog, FORM_CLASS):

    shapeFileName = None

    def __init__(self, iface):
        super(LPImportDialog, self).__init__(None)
        self.iface = iface
        self.setupUi(self)
        self.addProfileLineLayers()

        self.Btn_OpenFileSelectDialog.clicked.connect(self.getShapeFilePath)

    def accept(self):
        if self.checkParams():
            self.done(1)

    def checkParams(self):
        if self.RadBtn_FileSelect.isChecked() and \
           self.TBox_ShapeFilePath.text() == '':
            return False
        return True

    def getShapeFilePath(self):
        self.shapeFileName, _ = QFileDialog.getOpenFileName(
            self, 'Select a shape file', '~/', 'ESRI Shapefile (*.shp)')
        if self.shapeFileName:
            self.TBox_ShapeFilePath.setText(self.shapeFileName)
            if not self.checkShapeFileType():
                QMessageBox.information(
                    self, 'Error', 'Selected file is not appropriate')

    def checkShapeFileType(self):
        out = True
        profileLine = self.iface.addVectorLayer(
            self.shapeFileName, 'tmp', 'ogr')
        # print profileLine.geometryType()
        # print profileLine.featureCount()

        if profileLine.geometryType() != 1 or profileLine.featureCount() != 1:
            out = False
            self.TBox_ShapeFilePath.clear()
        QgsProject.instance().removeMapLayers([profileLine.id()])
        return out

    def addProfileLineLayers(self):
        canvas = self.iface.mapCanvas()
        for layer in canvas.layers():
            # vector layer
            if layer.type() == 0 and \
               layer.geometryType() == 1 and \
               layer.featureCount() == 1:
                self.CmbBox_LayerSelect.addItem(layer.name(), layer.id())
        self.RadBtn_LayerSelect.setEnabled(self.CmbBox_LayerSelect.count())
        self.CmbBox_LayerSelect.setEnabled(self.CmbBox_LayerSelect.count())
