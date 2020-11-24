"""
/***************************************************************************
 LineProfile
                                 A QGIS plugin
 Create line profiles from attribute table in vector layer and color band of raster layer
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-10-30
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Kouki Kitajima (WiscSIMS)
        email                : kitajima@wisc.edu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import os.path
import re
from functools import reduce

from qgis.PyQt.QtGui import QIcon

from qgis.PyQt.QtCore import (
    QSettings,
    QTranslator,
    QCoreApplication,
    QVariant,
    QTimer,
)
from qgis.PyQt.QtWidgets import (
    QAction,
    QFileDialog,
    QMessageBox,
)

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
    QgsPoint,
)

# Initialize Qt resources from file resources.py
from .resources import *

# Import tools
from .tools.plottingTool import PlottingTool
from .tools.profileLineTool import ProfileLineTool
from .tools.dataProcessingTool import DataProcessingTool
from .tools.myTableViewModel import MyTableViewModel
from .tools.profilePlotConverter import ProfiilePlotConverter

# Import UI (dock and dialogs)
from .ui.dockWidget import DockWidget
from .ui.lpExportDialog import LPExportDialog
from .ui.lpImportDialog import LPImportDialog
from .ui.lpConfigPlotDialog import LPConfigPlotDialog


class LineProfile:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'LineProfile_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&LineProfile')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'LineProfile')
        self.toolbar.setObjectName(u'LineProfile')

        # print "** INITIALIZING LineProfile"

        self.pluginIsActive = False
        self.dockwidget = None
        self.DockWidget = None

        self.dock = None
        self.dockOpened = False
        self.canvas = self.iface.mapCanvas()
        self.originalMapTool = self.canvas.mapTool()

        self.closingFlag = False
        self.debugFlag = False

        self.model = MyTableViewModel()

        self.timer = QTimer()
        self.timer2 = QTimer()

        self.timer_pixel_size_spin_box = QTimer()
        self.timer_pixel_size_spin_box.setSingleShot(True)

        self.n_profile_lines = 2
        self.pLines = []

        # instancialize tools
        self.profileLineTool = ProfileLineTool(self.canvas)
        self.plotTool = PlottingTool(self.model, self.drawTracer)
        self.dpTool = DataProcessingTool(self.n_profile_lines)
        self.ppc = ProfiilePlotConverter()

    # noinspection PyMethodMayBeStatic

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LineProfile', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/line_profile/img/icon.png'
        self.line_profile_action = self.add_action(
            icon_path,
            text=self.tr(u'Line Profile'),
            callback=self.run,
            whats_this=self.tr('Plot Line Profiles'),
            parent=self.iface.mainWindow())
        self.line_profile_action.setCheckable(True)

    # --------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        # print "** CLOSING LineProfile"
        # disconnects
        # self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        self.dock.closingPlugin.disconnect(self.onClosePlugin)
        self.line_profile_action.setChecked(False)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        # print "** UNLOAD LineProfile"

        self.pluginIsActive = False

        # clear objects on the canvas
        # rubberbands
        try:
            # self.profileLineTool.resetProfileLine(all=True)
            self.profileLineTool.reset_all_profile()
        except AttributeError:
            print(str(AttributeError))

        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&LineProfile'), action)
            self.iface.removeToolBarIcon(action)

        # remove the toolbar
        del self.toolbar

    # --------------------------------------------------------------------------

    def run(self):
        """Run method that loads and starts the plugin"""
        """execute when the plugin button get hit"""

        if self.pluginIsActive:
            self.line_profile_action.setChecked(True)
            return

        self.pluginIsActive = True

        if self.dock is None:

            # Create the dockwidget (after translation) and keep reference
            self.dock = DockWidget(self.iface.mainWindow(), self.iface, self.model)
            self.dock.showDockWidget()
            self.dockOpened = True
            self.dock.closingPlugin.connect(self.onClosePlugin)

            # Create plot area and add to the widget
            self.plotTool.addPlotWidget(self.dock.myFrame)
            self.init_profile_line()

            # Create UI-Action connections
            self.connectDock()

        # self.refreshProfileLines()
        self.init_map_tool()
        self.profileLineTool.show_profile_line()

    def refreshProfileLines(self):
        self.profileLineTool.show_profile_line()

    def adjustTableColumnWidth(self):
        self.timer.stop()
        try:
            w = 68 if self.dock.myTable.verticalScrollBar().isVisible() else 85
            self.dock.myTable.setColumnWidth(self.model.getColumnIndex('layer'), w)
        except Exception:
            pass

    def init_map_tool(self):

        self.prev_tool = self.canvas.mapTool()
        self.line_profile_action.setChecked(True)
        self.dock.setEnabled(True)

        # set canvas maptool to profileline tool
        self.canvas.setMapTool(self.profileLineTool)

        # create connection between changing maptool event and actoin (mapToolChanged)
        self.canvas.mapToolSet.connect(self.mapToolChanged)

    def mapToolChanged(self, current_maptool, old_maptool):
        # print('mapToolChanged')
        # changed to LineProfileTool
        if re.search(r'LineProfileTool', str(current_maptool)):
            self.dock.setEnabled(True)
            return

        # changed to other tools
        try:
            # disconnecting shold be done first
            # otherwise, mapToolChanged event happens again
            self.canvas.mapToolSet.disconnect(self.mapToolChanged)
            self.canvas.unsetMapTool(self.profileLineTool)

            """deactivate plugin"""

            # hide profile line rubberbands
            self.profileLineTool.hide_profile_line()
            # self.profileLineTool.hideProfileLine()

            # deactivate plugin button
            self.line_profile_action.setChecked(False)

            # deactivate dock widget
            self.dock.setEnabled(False)

            # set plugin state to deactivated
            self.pluginIsActive = False
        except Exception:
            pass

    def connectTools(self):
        self.profileLineTool.proflineterminated.connect(self.handle_terminate_profile_line)
        self.profileLineTool.doubleClicked.connect(self.resetPlot)

    def disconnectTools(self):
        try:
            self.profileLineTool.proflineterminated.disconnect(self.updatePlot)
            self.profileLineTool.doubleClicked.disconnect(self.resetPlot)
        except Exception:
            pass

    def myConnect(self):
        self.timer.start(50)
        self.updatePlot()
        try:
            w = 74 if self.dock.myTable.verticalScrollBar().isVisible() else 91
            self.dock.myTable.setColumnWidth(self.model.getColumnIndex('layer'), w)
        except Exception:
            pass

        self.update_area_sampling_list()

    def connectDock(self):

        self.connectTools()

        self.disconnectDock()

        # self.dock.closed.connect(self.closePlugin)
        self.dock.showConfig.connect(self.showConfigDialog)
        # self.dock.resized.connect(self.updatePlot)
        self.dock.resized.connect(self.windowResizeEvent)

        self.dock.myExportProfileLineBtn.clicked.connect(self.openExportProfileLineDialog)
        self.dock.Btn_ImportProfileLine.clicked.connect(self.openImportProfileLineDialog)
        self.dock.Btn_ExportPlot.clicked.connect(self.exportPlot)
        self.dock.ChkBox_TieLine.stateChanged.connect(self.updatePlot)
        self.dock.ChkBox_Tracer.stateChanged.connect(self.handle_toggle_tracking_marker)
        self.dock.ChkBox_ShowSamplingPoints.stateChanged.connect(self.handle_sampling_point_display)
        self.dock.ChkBox_ShowSamplingAreas.stateChanged.connect(self.handle_sampling_area_display)
        self.dock.Btn_ExportProfileData.clicked.connect(self.exportProfileData)
        self.dock.CmbBox_ProfileLine.currentIndexChanged.connect(self.changeCurrentProfileLine)
        self.dock.ChkBox_pLineNormalize.stateChanged.connect(self.updatePlot)

        self.dock.Btn_AddProfileLine.clicked.connect(self.clear_profile_line)

        self.dock.Spn_PixelSize.valueChanged.connect(self.update_pixel_size)

        self.dock.Grp_Normalized.clicked.connect(self.updatePlot)
        self.dock.Rdo_By_Total_Length.clicked.connect(self.updatePlot)
        self.dock.Rdo_By_Segment.clicked.connect(self.updatePlot)

        # model
        self.model.itemChanged.connect(self.myConnect)
        self.model.rowsInserted.connect(self.myConnect)
        self.model.rowsRemoved.connect(self.myConnect)

        # timers
        self.timer.timeout.connect(self.adjustTableColumnWidth)
        self.timer2.timeout.connect(self.windowResizeEventTimeOut)

        self.timer_pixel_size_spin_box.timeout.connect(self.updatePlot)

    def disconnectDock(self):
        try:
            self.dock.myExportProfileLineBtn.clicked.disconnect(self.openExportProfileLineDialog)
            self.dock.Btn_ImportProfileLine.clicked.disconnect(self.openImportProfileLineDialog)
            self.dock.Btn_ExportPlot.clicked.disconnect(self.exportPlot)
            self.dock.ChkBox_TieLine.stateChanged.disconnect(self.updatePlot)
            self.dock.ChkBox_ShowSamplingPoints.stateChanged.disconnect(self.updatePlot)
            self.dock.ChkBox_ShowSamplingAreas.stateChanged.disconnect(self.updatePlot)
            self.dock.Btn_ExportProfileData.clicked.disconnect(self.exportProfileData)
            self.dock.CmbBox_ProfileLine.currentIndexChanged.disconnect(
                self.changeCurrentProfileLine)
            self.dock.Btn_AddProfileLine.clicked.disconnect(self.addProfileLine)
            self.dock.ChkBox_pLineNormalize.stateChanged.disconnect(self.updatePlot)

            self.dock.resizeEvent = None

        # model
            self.model.itemChanged.disconnect(self.myConnect)
            self.model.rowsInserted.disconnect(self.myConnect)
            self.model.rowsRemoved.disconnect(self.myConnect)
            self.timer.timeout.disconnect(self.adjustTableColumnWidth)

        except Exception:
            pass

    def showConfigDialog(self, index):
        self.configPlotDialog = LPConfigPlotDialog(
            self.iface, self.model, index)
        self.configPlotDialog.show()

    def refreshModel(self):
        tree_root = QgsProject.instance().layerTreeRoot()
        # layers = legend.layers()
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        layerIds = [layer.id() for layer in layers]
        removeRows = []
        visRows = {}
        for r in range(self.model.rowCount()):
            lid = self.model.getLayerId(r)
            # exist vs. not exist
            if lid not in layerIds:
                removeRows.append(r)
            else:
                # visible vs. not visible
                state = tree_root.findLayer(lid).isVisible()
                # state = legend.isLayerVisible(layers[layerIds.index(lid)])
                mState = self.model.getCheckState(r)

                if state is False and mState == 2:
                    visRows[r] = 0
                    self.model.setCheckState(r, 0)

        removeRows.reverse()
        self.model.updateFlag = False
        [self.model.removeRows(r, 1) for r in removeRows]
        [self.model.setCheckState(r, s) for r, s in iter(visRows.items())]
        self.model.updateFlag = True
        if removeRows or visRows:
            self.updatePlot()

    def save_plot(self):
        self.exportPlot()

    def exportPlot(self):
        default_file_name = 'line_profile_image'
        project_path = QgsProject.instance().readPath('./')
        fileName, _ = QFileDialog.getSaveFileName(self.iface.mainWindow(),
                                                  "Save As",
                                                  os.path.join(
                                                      project_path, default_file_name),
                                                  "Portable Document Format (*.pdf);;\
                                               Image - PNG file (*.png);;\
                                               Image - JPEG file (*.jpg);;\
                                               Scalable Vector Graphics (*.svg)")
        if fileName:
            self.updatePlot()
            self.plotTool.savePlot(fileName)

    def windowResizeEvent(self):
        self.windowResizeState = True
        # print 'window resize start'

    def windowResizeEventTimeOut(self):
        if self.windowResizeState:
            pass

    def is_profileline_available(self, profile_line_points):
        n_points = 0
        for p in profile_line_points:
            n_points += len(p)
        return n_points != 0

    def show_alert_non_0_for_pixel_size(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)

        msg.setText("Pixel size must be greater than 0")
        msg.setInformativeText("This is additional information")
        msg.setWindowTitle("Error: Pixel Size")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def update_pixel_size(self, pixel_size):
        if pixel_size == 0:
            self.show_alert_non_0_for_pixel_size()
            self.dock.Spn_PixelSize.setValue(self.dpTool.pixel_size)
            return

        self.dpTool.pixel_size = pixel_size
        self.timer_pixel_size_spin_box.start(1000)

        # print('pixel size: ', self.dpTool.pixel_size)
    def get_raster_layer_id(self, row, layer_id, element_name):
        return '{}_{}_{}'.format(row, layer_id[-8:], element_name)

    def updatePlot(self):
        """ sampling/correct data from raster and vector layers along with profile line,
        then create/update plot
        """
        self.pLines = []

        if not self.model.updateFlag:
            return

        if self.canvas.layerCount() == 0 or self.model.rowCount() == 0:
            self.profileLineTool.reset_all_profile()
            # self.profileLineTool.resetProfileLine()
            self.plotTool.resetPlot(1)
            return

        profPoints = self.profileLineTool.get_all_profile_points()

        # self.pLines = []
        if not self.is_profileline_available(profPoints):
            # reset plot
            self.plotTool.resetPlot(clearAll=True)
            return

        for pIndex in range(len(profPoints)):
            pp = profPoints[pIndex]
            self.updateProfileLineData(pIndex, pp)
            self.pLines.append(self.dpTool.getProfileLines(pp))

        if len(self.pLines) == 2:
            if len(self.pLines[0]) == len(self.pLines[1]):
                self.ppc.set_pLines(self.pLines, 0)

        if reduce(lambda x, y: x + len(y), self.pLines, 0) == 0:
            return False

        # initialize tie lines
        self.dpTool.initTieLines()
        # self.profLineTool.resetTieLies()

        # reset sampling ranges
        # self.profileLineTool.resetSamplingRange()

        # initialize sampling points on raster layer for debugging
        self.dpTool.initSamplingPoints()
        self.dpTool.initSamplingArea()

        self.plotData = []
        # distLimit = self.dock.SpnBox_DistanceLimit.value()
        for pIndex in range(len(self.pLines)):
            pp = self.pLines[pIndex]
            if not len(pp):
                self.plotData.append([])
                continue
            data = []
            for r in range(self.model.rowCount()):
                layer = self.getLayerById(self.model.getLayerId(r))
                if not layer or not self.model.getCheckState(r):
                    continue

                field = self.model.getDataName(r)
                config = self.model.getConfigs(r)
                label = self.model.getDataName(r)
                color_org = self.model.getColorName(r)
                layer_type = layer.type()

                if layer_type == layer.VectorLayer:
                    """Vector Layer"""
                    myData = self.dpTool.getVectorProfile(
                        pp, layer, field, config['maxDistance'], None, pIndex)

                elif layer_type == layer.RasterLayer:
                    """Raster Layer"""
                    equi_width = int(config['areaSampling']) * \
                        config['areaSamplingWidth']
                    raster_layer_id = self.get_raster_layer_id(
                        r, layer.id(), label)
                    myData = self.dpTool.getRasterProfile(
                        pp, layer, field, config['fullRes'], raster_layer_id, equi_width, pIndex)
                    # draw raster sampling area and pionts

                data.append({'data': myData,
                             'label': label,
                             'configs': config,
                             'layer': layer,
                             'layer_type': layer_type,
                             'color_org': color_org})
            # self.handle_raster_sampling_details(pIndex, config, color_org)
            self.plotData.append(data)

        # draw tie lines
        if self.dock.ChkBox_TieLine.isChecked():
            self.profileLineTool.draw_tieline(self.dpTool.getTieLines())

        # draw sampling points and areas
        self.handle_sampling_point_display()
        self.handle_sampling_area_display()
        # draw sampling points on raster layer for debugging
        # if self.debugFlag is True:
        #     for pt in self.dpTool.getSamplingPoints():
        #         self.profileLineTool.addVertex5(pt)

        # self.profileLineTool.updateProfileLine()

        normalized = self.dock.Grp_Normalized.isChecked()
        normalized_by_segment = self.dock.Rdo_By_Segment.isChecked()

        """ check profile lines whether normalizable or not """
        if normalized and normalized_by_segment:
            n_seg = len(self.pLines[0])
            for i in range(1, len(self.pLines)):
                if n_seg != len(self.pLines[i]):
                    # Show message (need to have same number of segment)
                    self.show_error_message_on_normaliziation('Need same number of segments.')
                    return

        if normalized:
            for i in range(len(self.pLines)):
                if len(self.pLines[i]) == 0:
                    # Show message (need to have same number of segment)
                    self.show_error_message_on_normaliziation('At least two profile line needed.')
                    return

        """ draw plot """
        self.plotTool.drawPlot3(self.pLines, self.plotData, pLineNormalized=normalized,
                                pLineNormalizedBySegment=normalized_by_segment)

    def show_error_message_on_normaliziation(self, text):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(text)
        msg.setWindowTitle("Error: Normalization")
        msg.exec_()
        pass

    def handle_sampling_point_display(self):
        """ handle show/hide sampling points """

        self.hide_all_sampling_points()
        if self.dock.ChkBox_ShowSamplingPoints.isChecked():
            [self.show_sampling_points(profile_index) for profile_index in range(
                self.n_profile_lines) if len(self.profileLineTool.profile[profile_index]['point'])]

    def show_sampling_points(self, profile_index):
        """draw sampling points """
        current_id = self.dock.ChkBox_Area_Sampling_Element.currentIndex()
        layer_id = self.dock.ChkBox_Area_Sampling_Element.itemData(current_id)
        ks = self.dpTool.sampling_points[profile_index].keys()

        if layer_id in ks:
            sampling_pts = self.dpTool.sampling_points[profile_index][layer_id]
            self.profileLineTool.add_sampling_points(
                profile_index, sampling_pts)

    def hide_all_sampling_points(self):
        [self.hide_sampling_points(profile_index) for profile_index in range(self.n_profile_lines)]

    def hide_sampling_points(self, profile_index):
        self.profileLineTool.reset_sampling_points(profile_index)

    def handle_sampling_area_display(self):
        """ handle show/hide sampling areas """
        self.hide_all_sampling_areas()
        if self.dock.ChkBox_ShowSamplingAreas.isChecked():
            [self.show_sampling_areas(profile_index) for profile_index in range(
                self.n_profile_lines) if len(self.profileLineTool.profile[profile_index]['point'])]

    def show_sampling_areas(self, profile_index):
        """ draw sampling areas belong to specified profile line """
        current_id = self.dock.ChkBox_Area_Sampling_Element.currentIndex()
        layer_id = self.dock.ChkBox_Area_Sampling_Element.itemData(current_id)
        ks = self.dpTool.sampling_points[profile_index].keys()

        if layer_id in ks:
            sampling_areas = self.dpTool.sampling_areas[profile_index][layer_id]
            self.profileLineTool.add_sampling_areas(profile_index, sampling_areas)

    def hide_all_sampling_areas(self):
        """ remove all sampling areas for all profile lines """
        [self.hide_sampling_areas(profile_index) for profile_index in range(self.n_profile_lines)]

    def hide_sampling_areas(self, profile_index):
        """ remove sampling area belong to specified profile line """
        self.profileLineTool.reset_sampling_areas(profile_index)

    def handle_raster_sampling_details(self, p_index, config, color_org):
        """draw raster sampling area and points"""

        self.profileLineTool.reset_sampling_areas(p_index)
        self.profileLineTool.reset_raster_sampling_points(p_index)

        if config['areaSampling']:
            # add sampling area
            if self.dock.ChkBox_ShowSamplingAreas.isChecked():
                self.profileLineTool.add_sampling_areas(
                    self.dpTool.getSamplingArea(), color_org)

            # add sampling points
            if self.dock.ChkBox_ShowSamplingPoints.isChecked():
                for pt in self.dpTool.getSamplingRange():
                    self.profileLineTool.add_sampling_points(pt, color_org)

    def resetPlot(self):
        resetAllFlag = False
        if reduce(lambda x, y: x + len(y), self.profileLineTool.getAllProfPoints(), 0) == 0:
            resetAllFlag = True
        self.plotTool.resetPlot(resetAllFlag)
        self.updatePlot()

    def openExportProfileLineDialog(self):
        self.expPLDialog = LPExportDialog()
        self.expPLDialog.show()
        res = self.expPLDialog.exec_()
        if not res:
            return

        if self.expPLDialog.Grp_SaveShapeFileAs.isChecked():
            shapeFilePath = self.sanitizePath(
                self.expPLDialog.shapeFileName)
            self.exportProfileLineAsShapeFile(shapeFilePath)
        if self.expPLDialog.Grp_AddField.isChecked():
            self.addDistanceToAttribute()

    def exportProfileLineAsShapeFile(self, shapeFilePath):
        fields = []
        polyline = []
        attr = []
        fileName = os.path.basename(shapeFilePath.split(os.extsep)[0])
        profileLineLayer = QgsVectorLayer('LineString', fileName, 'memory')

        profileLineLayer.startEditing()
        dataProvider = profileLineLayer.dataProvider()

        # get point of current profile line
        points = self.profileLineTool.get_profile_points()

        # add fields
        for i in range(len(points)):
            fields.append(QgsField('Point-{0}'.format(i + 1), QVariant.String))
        fields.append(QgsField('Max Dist.', QVariant.Double))
        dataProvider.addAttributes(fields)

        # get rofile line features
        for pt in points:
            polyline.append(QgsPoint(*pt))
            attr.append('{0}, {1}'.format(*pt))

        # add a feature
        feture = QgsFeature()
        feture.setGeometry(QgsGeometry.fromPolyline(polyline))
        feture.setAttributes(attr)
        dataProvider.addFeatures([feture])

        # update layer's extent when new features have been added
        # because change of extent in provider is not propagated to the layer
        profileLineLayer.commitChanges()
        profileLineLayer.updateExtents()

        # save shape file
        error, _ = QgsVectorFileWriter.writeAsVectorFormat(profileLineLayer,
                                                           shapeFilePath,
                                                           'UTF-8',
                                                           driverName='ESRI Shapefile')
        if error == QgsVectorFileWriter.NoError:
            if self.expPLDialog.ChkBox_AddSavedFileToMap.isChecked():
                # add shape file to map
                self.iface.addVectorLayer(shapeFilePath, fileName, 'ogr')
        else:
            pass

    def is_layer_available(self, layer, model, r):
        if not layer:
            return False
        if not layer.RasterLayer:
            return False
        if not model.getCheckState(r):
            return False
        return True

    def addDistanceToAttribute(self):

        newFieldName = self.expPLDialog.TBox_FieldName.text()

        for r in range(self.model.rowCount()):
            layer = self.getLayerById(self.model.getLayerId(r))

            if not self.is_layer_available(layer, self.model, r):
                continue

            field = self.model.getDataName(r)
            config = self.model.getConfigs(r)
            pIndex = self.getProfileIndex()
            dataProvider = layer.dataProvider()
            dataProvider.addAttributes(
                [QgsField(newFieldName, QVariant.Double)])
            layer.updateFields()
            self.dpTool.getVectorProfile(self.pLines[pIndex],
                                         layer,
                                         field,
                                         config['maxDistance'],
                                         newFieldName,
                                         pIndex)

    def openImportProfileLineDialog(self):
        self.impPLDialog = LPImportDialog(self.iface)
        self.impPLDialog.show()

        if not self.impPLDialog.exec_():
            return

        if self.impPLDialog.RadBtn_FileSelect.isChecked():
            shapeFilePath = self.sanitizePath(
                self.impPLDialog.TBox_ShapeFilePath.text())
            shapeFileName = os.path.basename(shapeFilePath.split(os.extsep)[1])
            layer = self.iface.addVectorLayer(
                shapeFilePath, shapeFileName, 'ogr')
        else:
            layerId = self.impPLDialog.CmbBox_LayerSelect.itemData(
                self.impPLDialog.CmbBox_LayerSelect.currentIndex())
            layer = self.getLayerById(layerId)
        self.importProfileLine(layer)

    def importProfileLine(self, layer):

        dp = layer.dataProvider()
        for f in dp.getFeatures():
            points = f.geometry().asMultiPolyline()
        points = [[pt.x(), pt.y()] for pt in points[0]]
        self.profileLineTool.draw_profileLine_from_points(points)
        self.updatePlot()

    def init_profile_line(self):
        for i in range(self.n_profile_lines):
            self.dock.CmbBox_ProfileLine.addItem(
                'Profile Line {}'.format(i + 1), i)
        self.dock.CmbBox_ProfileLine.setCurrentIndex(0)

        # self.profileLineTool.initProfileLine(n)
        self.profileLineTool.init_profile(self.n_profile_lines)

    def clear_profile_line(self):
        # self.profileLineTool.resetProfileLine()
        self.profileLineTool.reset_profile(self.getProfileIndex())
        self.updatePlot()

    def removeProfileLine(self):
        """remove second profile line"""
        pass

    def changeCurrentProfileLine(self, pIndex):
        self.profileLineTool.update_current_profile_line(pIndex)

    def getProfileIndex(self):
        return self.dock.CmbBox_ProfileLine.currentIndex()

    def updateProfileLineData(self, pIndex, data):
        self.dock.CmbBox_ProfileLine.setItemData(pIndex, data)
        self.profileLineTool.terminated = True

    def check_tracer_condition(self, event, pIndex, normFactor):
        res = not self.dock.ChkBox_Tracer.isChecked() \
            or event.xdata is None \
            or event.ydata is None \
            or len(self.pLines) < pIndex \
            or len(normFactor) <= pIndex

        # res5 = not (self.dock.ChkBox_Tracer.isChecked
        #             and event.xdata
        #             and event.ydata
        #             and len(self.pLines) >= pIndex
        #             and len(normFactor) > pIndex)
        # print('tracer check:', res, ' - ', res5)
        return res

    def handle_toggle_tracking_marker(self, state):
        if state:
            self.profileLineTool.init_tracking_marker()
        else:
            self.profileLineTool.reset_tracking_marker()

    def is_trace_marker_available(self, event):
        if not self.dock.ChkBox_Tracer.isChecked():
            return False

        if not (event.xdata and event.ydata):
            return False

        if len(self.profileLineTool.profile[self.profileLineTool.profile_line_index]['point']) == 0:
            return False

        return True

    def draw_trace_marker(self, event, normFactor):
        # self.profileLineTool.reset_tracing_marker()
        if not self.is_trace_marker_available(event):
            # hide marker
            self.profileLineTool.hide_tracking_marker()
            return

        p_index = self.profileLineTool.profile_line_index
        # show marker
        self.profileLineTool.show_tracking_marker()

        # move marker to the position

        # normalized by segment
        if self.is_normalized_by_segment():
            x = self.ppc.plotX_to_profileX(event.xdata, p_index)
        else:
            x = event.xdata / normFactor[p_index]

        if x > self.dpTool.sumD(self.pLines[p_index]):
            return
        pt = self.dpTool.getCurrentCoordinates(self.pLines[p_index], x)
        self.profileLineTool.update_tracking_marker(pt)

    def is_normalized_by_segment(self):
        return self.dock.Grp_Normalized.isChecked() and self.dock.Rdo_By_Segment.isChecked()

    def drawTracer(self, event, normFactor):
        self.draw_trace_marker(event, normFactor)
        return
        # self.profileLineTool.resetRasterPoints()
        # self.profileLineTool.reset_tracing_marker()
        # pIndex = self.dock.CmbBox_ProfileLine.currentIndex()
        # if self.check_tracer_condition(event, pIndex, normFactor):
        #     return
        #
        # x = event.xdata / normFactor[pIndex]
        #
        # if self.dpTool.sumD(self.pLines[pIndex]) < x:
        #     return
        #
        # pt = self.dpTool.getCurrentCoordinates(self.pLines[pIndex], x)
        # self.profileLineTool.add_tracing_marker(pt)

    def handle_terminate_profile_line(self):
        # update profile-plot converter
        self.updatePlot()

    def exportProfileData(self):
        fileName, _ = QFileDialog.getSaveFileName(self.iface.mainWindow(),
                                                  "Save As",
                                                  os.environ['HOME'],
                                                  "Tab Deliminated Text (*.txt);; Comma Separated Values (*.csv)")
        if fileName:
            myD = []
            myL = 0
            out = []
            filePath, fileType = os.path.splitext(fileName)
            if fileType == '.txt':
                sep = "\t"
            elif fileType == '.csv':
                sep = ","
            else:
                sep = " "
            pIndex = self.getProfileIndex()
            data = self.plotData[pIndex]

            for d in data:
                if d['configs']['movingAverage']:
                    d['data'] = self.plotTool.calculateMovingAverage(d['data'],
                                                                     d['configs']['movingAverageN'])
                curL = len(d['data'][0])
                myL = curL if curL >= myL else myL

            for d in data:
                label = d['layer'].name() + '_' + d['label']
                # transpose data rows and columns
                a = [list(x) for x in zip(*d['data'])]
                curL = len(a)
                # padded by '' for shorter data length
                for n in range(myL - curL):
                    a.append(['', ''])
                a.insert(0, ['distance (micron)', label])
                myD.append(a)

            for r in range(myL + 1):  # plus 1 for label
                l = []
                for c in myD:
                    l += c[r]
                out.append(sep.join(str(ll) for ll in l))

            with open(fileName, 'w') as f:
                f.write("\n".join(out))

    def getLayerById(self, lid):
        l = [layer for layer in self.canvas.layers() if lid == layer.id()]
        return l[0] if len(l) == 1 else False

    def update_area_sampling_list(self):
        my_cbx = self.dock.ChkBox_Area_Sampling_Element
        my_cbx.clear()
        for r in range(self.model.rowCount()):
            element_name = self.model.getDataName(r)
            layer_id = self.model.getLayerId(r)
            layer_type = self.model.getLayerTypeName(r)
            if layer_type == 'Vector':
                continue
            raster_layer_id = self.get_raster_layer_id(
                r, layer_id, element_name)
            my_cbx.addItem(element_name, raster_layer_id)

    def sanitizePath(self, path):
        path = os.path.expanduser(path)
        path = os.path.expandvars(path)
        return os.path.abspath(path)
