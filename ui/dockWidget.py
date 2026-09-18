import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QMessageBox,
    QInputDialog,
    QColorDialog,
    QComboBox,
    QHeaderView,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qgis.PyQt.QtCore import (
    QSize,
    QTimer,
    Qt,
    pyqtSignal
)

from qgis.core import QgsProject
from .cwtSettingsDialog import CwtSettingsDialog
from ..tools.peakDetectionTool import ALGORITHM_STANDARD, ALGORITHM_CWT, DEFAULT_CWT_SETTINGS
from ..tools.uiLayoutState import peak_control_visibility

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'dockWidget.ui'))


class CompactNavigationList(QListWidget):
    """A content-sized page selector that remains readable with scaled fonts."""

    def sizeHint(self):
        hint = super().sizeHint()
        text_width = max(
            (self.fontMetrics().horizontalAdvance(self.item(row).text())
             for row in range(self.count())),
            default=0,
        )
        return QSize(text_width + 2 * self.frameWidth() + 20, hint.height())


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
        self.initPageNavigation()
        self.initPeakDetectionLayout()
        self.initTableView()
        self.initPeakDetectionControls()
        self.connectTable()
        self.pageNavigation.setCurrentRow(0)
        self.myFrame_2.hide()
        self.widget_3.show()

    def initPageNavigation(self):
        """Replace the tab strip with compact, horizontal-text left navigation."""
        old_tabs = self.tabWidget_2
        pages = [old_tabs.widget(index) for index in range(old_tabs.count())]
        for page in pages:
            old_tabs.removeTab(0)

        container = QWidget(self.dockWidgetContents)
        container.setObjectName("dockPageContainer")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        navigation = CompactNavigationList(container)
        navigation.setObjectName("pageNavigation")
        navigation.addItems(("Plot", "Options", "Dev"))
        navigation.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        navigation.setSelectionMode(QAbstractItemView.SingleSelection)
        navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        navigation.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        navigation.setUniformItemSizes(True)
        navigation.setToolTip("Choose the Line Profile page")

        stack = QStackedWidget(container)
        stack.setObjectName("pageStack")
        stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for page in pages:
            stack.addWidget(page)

        layout.addWidget(navigation)
        layout.addWidget(stack, 1)
        self.horizontalLayout_2.replaceWidget(old_tabs, container)
        old_tabs.deleteLater()

        # Preserve the long-standing attribute for internal compatibility.
        self.tabWidget_2 = stack
        self.pageNavigation = navigation
        navigation.currentRowChanged.connect(stack.setCurrentIndex)

    @staticmethod
    def _compact_layout(layout):
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        return layout

    def _section_toggle(self, name, text, content, expanded=False):
        button = QToolButton(self.Grp_PeakDetection)
        button.setObjectName(name)
        button.setText(text)
        button.setCheckable(True)
        button.setChecked(expanded)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setAutoRaise(True)
        button.setToolTip("Show or hide {} controls".format(text))
        content.setVisible(expanded)

        def toggle(checked):
            content.setVisible(checked)
            button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

        button.toggled.connect(toggle)
        return button

    def initPeakDetectionLayout(self):
        """Reorganize the existing controls without changing their object names."""
        old_layout = self.gridLayout_PeakDetection
        while old_layout.count():
            old_layout.takeAt(0)
        old_layout.setContentsMargins(0, 0, 0, 0)
        old_layout.setSpacing(0)

        sections = QWidget(self.Grp_PeakDetection)
        sections.setObjectName("peakDetectionSections")
        sections_layout = self._compact_layout(QVBoxLayout(sections))

        detection = QGroupBox("Detection", sections)
        detection.setObjectName("Grp_DetectionSettings")
        self.Grp_DetectionSettings = detection
        detection_layout = self._compact_layout(QGridLayout(detection))
        detection_layout.setColumnStretch(1, 1)
        detection_layout.setColumnStretch(3, 1)

        self.Cmb_PeakDataSource.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.Cmb_PeakDataSource.setMinimumContentsLength(18)

        detection_layout.addWidget(self.Lbl_PeakDataSource, 0, 0)
        detection_layout.addWidget(self.Cmb_PeakDataSource, 0, 1, 1, 3)
        detection_layout.addWidget(self.Lbl_DetectionScope, 1, 0)
        detection_layout.addWidget(self.Cmb_DetectionScope, 1, 1, 1, 3)
        range_row = QWidget(detection)
        range_row.setObjectName("Wdg_DetectionRangeRow")
        range_layout = self._compact_layout(QHBoxLayout(range_row))
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.addWidget(self.Txt_DetectionRanges, 1)
        range_layout.addWidget(self.Btn_PickDetectionRange)
        detection_layout.addWidget(range_row, 2, 0, 1, 4)
        self.Wdg_DetectionRangeRow = range_row

        detection_layout.addWidget(self.Chk_DetectPeaks, 3, 0, 1, 2)
        detection_layout.addWidget(self.Chk_DetectValleys, 3, 2, 1, 2)
        detection_layout.addWidget(self.Lbl_PeakAlgorithm, 4, 0)
        detection_layout.addWidget(self.Cmb_PeakAlgorithm, 4, 1, 1, 2)
        detection_layout.addWidget(self.Btn_CwtSettings, 4, 3)
        detection_layout.addWidget(self.Lbl_ProminenceMode, 5, 0)
        detection_layout.addWidget(self.Cmb_ProminenceMode, 5, 1, 1, 3)
        detection_layout.addWidget(self.Lbl_Prominence, 6, 0)
        detection_layout.addWidget(self.Spn_Prominence, 6, 1, 1, 3)

        adaptive_row = QWidget(detection)
        adaptive_row.setObjectName("Wdg_AdaptiveWindowRow")
        adaptive_layout = self._compact_layout(QHBoxLayout(adaptive_row))
        adaptive_layout.setContentsMargins(0, 0, 0, 0)
        adaptive_layout.addWidget(self.Lbl_AdaptiveWindow)
        adaptive_layout.addWidget(self.Spn_AdaptiveWindow, 1)
        detection_layout.addWidget(adaptive_row, 7, 0, 1, 4)
        self.Wdg_AdaptiveWindowRow = adaptive_row

        detection_layout.addWidget(self.Lbl_MinPeakDistance, 8, 0)
        detection_layout.addWidget(self.Spn_MinPeakDistance, 8, 1, 1, 3)
        detection_layout.addWidget(self.Lbl_MinPeakWidth, 9, 0)
        detection_layout.addWidget(self.Spn_MinPeakWidth, 9, 1, 1, 3)

        detect_actions = QWidget(detection)
        detect_actions.setObjectName("Wdg_DetectionActions")
        detect_actions_layout = self._compact_layout(QHBoxLayout(detect_actions))
        detect_actions_layout.setContentsMargins(0, 0, 0, 0)
        detect_actions_layout.addWidget(self.Btn_AutoDetect)
        detect_actions_layout.addWidget(self.Btn_ClearAuto)
        detection_layout.addWidget(detect_actions, 10, 0, 1, 4)
        sections_layout.addWidget(detection)

        manual_content = QWidget(sections)
        manual_content.setObjectName("Wdg_ManualEditingContent")
        manual_layout = self._compact_layout(QHBoxLayout(manual_content))
        for button in (
            self.Btn_ModeSelect,
            self.Btn_ModeAddPeak,
            self.Btn_ModeAddValley,
            self.Btn_ModeDelete,
        ):
            button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            manual_layout.addWidget(button)
        manual_layout.addSpacing(4)
        manual_layout.addWidget(self.Lbl_SnapRange)
        manual_layout.addWidget(self.Spn_SnapRange)
        self.Wdg_ManualEditingContent = manual_content
        self.Btn_ToggleManualEditing = self._section_toggle(
            "Btn_ToggleManualEditing", "Manual Editing", manual_content
        )
        sections_layout.addWidget(self.Btn_ToggleManualEditing)
        sections_layout.addWidget(manual_content)

        points_content = QWidget(sections)
        points_content.setObjectName("Wdg_PointsContent")
        points_layout = self._compact_layout(QGridLayout(points_content))
        points_layout.addWidget(self.Chk_ShowFeaturePoints, 0, 0)
        points_layout.addWidget(self.Lbl_FeatureCount, 0, 1)
        points_layout.addWidget(self.Btn_PointsMenu, 0, 2)
        points_layout.addWidget(self.Btn_ClearInScope, 1, 0, 1, 2)
        points_layout.addWidget(self.Btn_ClearAllFeatures, 1, 2)
        points_layout.setColumnStretch(0, 1)
        self.Wdg_PointsContent = points_content
        self.Btn_TogglePoints = self._section_toggle(
            "Btn_TogglePoints", "Points", points_content
        )
        sections_layout.addWidget(self.Btn_TogglePoints)
        sections_layout.addWidget(points_content)
        sections_layout.addStretch(1)
        old_layout.addWidget(sections, 0, 0)

        scroll = QScrollArea(self.widget_3)
        scroll.setObjectName("PeakDetectionScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.horizontalLayout_4.replaceWidget(self.Grp_PeakDetection, scroll)
        self.Grp_PeakDetection.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        scroll.setWidget(self.Grp_PeakDetection)
        self.PeakDetectionScrollArea = scroll

    def initPeakDetectionControls(self):
        self.cwt_settings = dict(DEFAULT_CWT_SETTINGS)
        self.Cmb_PeakAlgorithm.setItemData(0, ALGORITHM_STANDARD)
        self.Cmb_PeakAlgorithm.setItemData(1, ALGORITHM_CWT)
        self.Cmb_PeakAlgorithm.currentIndexChanged.connect(self.updateAlgorithmControls)
        self.Cmb_ProminenceMode.currentIndexChanged.connect(self.updateConditionalControls)
        self.Cmb_DetectionScope.currentIndexChanged.connect(self.updateConditionalControls)
        self.Btn_CwtSettings.clicked.connect(self.showCwtSettings)
        self.updateConditionalControls()
        self.peakModeGroup = QButtonGroup(self)
        self.peakModeGroup.setExclusive(True)
        for button in (
            self.Btn_ModeSelect,
            self.Btn_ModeAddPeak,
            self.Btn_ModeAddValley,
            self.Btn_ModeDelete,
        ):
            self.peakModeGroup.addButton(button)

    def updateAlgorithmControls(self):
        self.updateConditionalControls()

    def updateConditionalControls(self):
        state = peak_control_visibility(
            self.Cmb_ProminenceMode.currentIndex(),
            self.Cmb_DetectionScope.currentIndex(),
            self.Cmb_PeakAlgorithm.currentData(),
        )
        self.Wdg_AdaptiveWindowRow.setVisible(state["adaptive_window"])
        self.Wdg_DetectionRangeRow.setVisible(state["selected_ranges"])
        self.Btn_CwtSettings.setVisible(state["cwt_settings"])
        self.Btn_CwtSettings.setEnabled(state["cwt_settings"])
        if state["selected_ranges"]:
            QTimer.singleShot(0, self.showDetectionRangeEditor)

    def showDetectionRangeEditor(self):
        """Bring the newly disclosed range editor into the scroll viewport."""
        if self.Cmb_DetectionScope.currentIndex() != 1:
            return
        self.PeakDetectionScrollArea.ensureWidgetVisible(
            self.Wdg_DetectionRangeRow, 0, 8
        )

    def showCwtSettings(self):
        dialog = CwtSettingsDialog(self.cwt_settings, self)
        if dialog.exec_():
            self.cwt_settings = dialog.settings()
        dialog.deleteLater()

    def connectTable(self):
        self.Btn_Add.clicked.connect(self.selectElement)
        self.myTable.doubleClicked.connect(self.modifyTable)
        self.myTable.clicked.connect(self.changeCheckState)

    def disconnectTable(self):
        for signal, callback in (
            (self.Btn_Add.clicked, self.selectElement),
            (self.myTable.doubleClicked, self.modifyTable),
            (self.myTable.clicked, self.changeCheckState),
        ):
            try:
                signal.disconnect(callback)
            except (RuntimeError, TypeError):
                pass

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
        hidden_columns = ('layerId', 'layerType')
        for name in hidden_columns:
            myT.setColumnHidden(self.model.getColumnIndex(name), True)

        header = myT.horizontalHeader()
        for name in ('state', 'color', 'config'):
            header.setSectionResizeMode(
                self.model.getColumnIndex(name),
                QHeaderView.ResizeToContents,
            )
        for name in ('layer', 'data'):
            header.setSectionResizeMode(
                self.model.getColumnIndex(name),
                QHeaderView.Stretch,
            )

        myT.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.model.updateFlag = True

    def showSelectDialog(self, layer, row=-1):
        myList = []
        dataType = "Attribute"  # or band
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
                                "Line Profile", "Please select one layer")
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
        if clickedCol == self.model.getColumnIndex('config'):
            self.showConfigWindow(model_item_index)
        elif clickedCol == self.model.getColumnIndex('state'):
            self.showHidePlot(model_item_index)
        elif clickedCol == self.model.getColumnIndex('color'):
            self.changeColor(model_item_index)
        # or clickedCol is 2:
        elif clickedCol == self.model.getColumnIndex('data'):
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
        if newColor.isValid() and newColor.name() != curColor.name():
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
