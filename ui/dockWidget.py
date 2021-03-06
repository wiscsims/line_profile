import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QMessageBox,
    QInputDialog,
    QColorDialog,
    QHeaderView
)
from qgis.PyQt.QtCore import (
    Qt,
    pyqtSignal
)

from qgis.core import QgsProject

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dockWidget.ui'))


class DockWidget(QDockWidget, FORM_CLASS):
    """DockWiget"""

    plotWdg = None
    closingPlugin = pyqtSignal()
    resized = pyqtSignal()
    showConfig = pyqtSignal(object)

    def __init__(self, parent, iface1, model):
        """Constructor."""
        super(DockWidget, self).__init__(parent)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self.iface = iface1
        self.canvas = self.iface.mapCanvas()
        self.model = model
        self.setupUi(self)
        self.initTableView()
        self.connectTable()
        self.tabWidget_2.setCurrentIndex(0)
        self.myFrame_2.hide()
        self.widget_3.show()

    def connectTable(self):
        self.Btn_Add.clicked.connect(self.selectElement)
        self.myTable.doubleClicked.connect(self.modifyTable)
        self.myTable.clicked.connect(self.changeCheckState)

    def disconnectTable(self):
        self.Btn_Add.clicked.disconnect(self.selectElement)
        self.myTable.doubleClicked.disconnect(self.modifyTable)
        self.myTable.clicked.disconnect(self.changeCheckState)

    def closeEvent(self, event):
        self.disconnectTable()
        self.closingPlugin.emit()
        event.accept()

    def showDockWidget(self):
        self.location = Qt.BottomDockWidgetArea

        # Draw the widget
        self.iface.addDockWidget(self.location, self)

    """
    ######################################################
    """

    # tableview
    def initTableView(self):
        myT = self.myTable
        myT.setModel(self.model)
        myT.horizontalHeader().setMinimumSectionSize(6)
        hiddenColumns = ['layerId', 'layerType']
        [myT.setColumnHidden(self.model.getColumnIndex(c), True) for c in hiddenColumns]
        # table width = 250
        columnSettings = {
            'state': {'width': 25},
            'color': {'width': 6},
            'layer': {'width': 95},
            'data': {'width': 100},
            'config': {'width': 24},
        }

        for c, v in iter(columnSettings.items()):
            c_index = self.model.getColumnIndex(c)
            myT.setColumnWidth(c_index, v['width'])
            myT.horizontalHeader().setSectionResizeMode(c_index, QHeaderView.Fixed)
        self.model.updateFlag = True

    def showSelectDialog(self, layer, row=-1):
        myList = []
        dataType = "Attibute"  # or band
        if layer.type() == layer.RasterLayer:  # Raster
            dataType = "Band"
            [myList.append('Band {}'.format(i + 1))
                for i in range(layer.bandCount())]
        elif layer.type() == layer.VectorLayer:  # Vector
            fields = layer.dataProvider().fields()
            [myList.append(f.name())
                for f in fields if f.type() == 2 or f.type() == 6]
        else:
            return False

        cIndex = myList.index(self.model.getDataName(row)) if row > 0 else 0

        ele, ok = QInputDialog.getItem(self.iface.mainWindow(),
                                       "Data Selector [" + layer.name() + "]",
                                       "Choose " + dataType, myList,
                                       cIndex, False)

        return ele if ok else False

    def selectElement(self):
        if self.iface.mapCanvas().layerCount() == 0:
            return

        if self.iface.activeLayer() is None:
            QMessageBox.warning(self.iface.mainWindow(),
                                "test", "Please select one layer")
            return
        else:
            cLayer = self.iface.activeLayer()

        selElem = self.showSelectDialog(cLayer)

        if selElem:
            self.model.addElement(cLayer, selElem)
        else:
            return

    def resizeEvent(self, event):
        self.resized.emit()

    def changeCheckState(self, index):
        if index.column() > 0:
            return
        row = index.row()

        layer_id = self.model.getLayerId(row)

        legend = QgsProject.instance().layerTreeRoot().findLayer(layer_id)

        layer = self.getLayerById(layer_id)
        if not layer or not legend.isVisible():
            self.model.setCheckState(row, 0)

    def modifyTable(self, model_item_index):

        clickedCol = model_item_index.column()
        if clickedCol is self.model.getColumnIndex('config'):
            self.showConfigWindow(model_item_index)
        elif clickedCol is self.model.getColumnIndex('state'):
            self.showHidePlot(model_item_index)
        elif clickedCol is self.model.getColumnIndex('color'):
            self.changeColor(model_item_index)
        # or clickedCol is 2:
        elif clickedCol is self.model.getColumnIndex('data'):
            self.changeData(model_item_index)
        else:
            return

    def showHidePlot(self, index):
        pass

    def showConfigWindow(self, model_item_index):
        self.showConfig.emit(model_item_index)

    def changeColor(self, index):
        row = index.row()
        curColor = self.model.getColor(row)
        newColor = QColorDialog().getColor(curColor)
        if newColor.isValid() and newColor.name() is not curColor.name():
            self.model.setColor(row, newColor)

    def changeData(self, index):
        row = index.row()
        for l in self.iface.mapCanvas().layers():
            if l.id() == self.model.getLayerId(row):
                selElem = self.showSelectDialog(l, row)
                if selElem:
                    self.model.setDataName(row, selElem)
                return

    def getLayerById(self, lid):
        l = [layer for layer in self.canvas.layers() if lid == layer.id()]
        return l[0] if len(l) == 1 else False
