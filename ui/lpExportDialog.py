# -*- coding: utf-8 -*-
# from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.PyQt import uic

import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'lpExportDialog.ui'))


class LPExportDialog(QDialog, FORM_CLASS):

    shapeFileName = None

    def __init__(self, parent=None):
        super(LPExportDialog, self).__init__(parent)
        self.setupUi(self)

        self.Btn_SaveAs.clicked.connect(self.getShapeFileName)

    def accept(self):
        if self.checkParams():
            self.done(1)

    def checkParams(self):
        if self.Grp_SaveShapeFileAs.isChecked() and \
           self.TBox_SaveFilePath.text() == '':
            QMessageBox.information(self, "Error", "Select shape file path")
        elif self.Grp_AddField.isChecked() and \
                self.TBox_FieldName.text() == '':
            QMessageBox.information(self, "Error", "Select field name")
        else:
            return True
        return False

    def getShapeFileName(self):
        self.shapeFileName, _ = QFileDialog.getSaveFileName(
            self, 'Save as', '~/', 'ESRI Shapefile (*.shp)')
        print(self.shapeFileName)
        if self.shapeFileName:
            self.TBox_SaveFilePath.setText(self.shapeFileName)
