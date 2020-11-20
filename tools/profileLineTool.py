from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsPointXY, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand, QgsVertexMarker


class ProfileLineTool(QgsMapTool):

    doubleClicked = pyqtSignal()
    proflineterminated = pyqtSignal()

    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas

        self.scene = self.canvas.scene()
        self.terminated = True
        self.profile_line_index = 0
        self.profile_lines = []

        self.profile_line_points = []

        self.profile = []
        """
         data structure of each profile line
         {
           'point': [QgsPointXY()-1], [QgsPointXY()-2], ...],
           'markers': {
                'line': rb_line,
                'vertex': [rb_vertex1, rb_vertex2, ...],
                'tieline': [rb_tieline1, rb_tieline2, ...],
                'sampling_area': [rb_sampling_area1, rb_sampling_area2, ...],
                'sampling_point': [rb_sampling_point1, rb_sampling_point2, ...],
           }
         }
        """

        self.plColor = [QColor(255, 20, 20, 250),
                        QColor(20, 20, 255, 250),
                        QColor(20, 255, 20, 250)]

        self.flag_double_clicked = False

        self.tracking_marker = None

        # print('INIT PROFILELINETOOL')

    def get_default_profile(self, idx=0):
        # set rubberband properties
        # False = not a polygon
        rb_line = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        rb_line.setWidth(2)
        rb_line.setIcon(QgsRubberBand.ICON_CIRCLE)
        rb_line.setColor(self.plColor[idx])

        default_profile = {
            'point': [],
            'markers': {
                'line': rb_line,
                'vertex': [],
                'tieline': [],
                'sampling_area': [],
                'sampling_point': []
            }
        }

        return default_profile

    def init_profile(self, n_profile_line):
        for profile_index in range(n_profile_line):
            default_profile = self.get_default_profile(profile_index)
            self.profile.append(default_profile)

    def reset_all_profile(self):
        [self.reset_profile(idx) for idx in range(len(self.profile))]
        self.hide_tracking_marker()

    def reset_profile(self, profile_index):
        # reset points
        self.profile[profile_index]['point'] = []

        # reset rubberband
        #   - line
        self.profile[profile_index]['markers']['line'].reset()

        try:
            #   - vertex
            # reset vertex rubberbands (delete from canvas)
            [vtx.reset() and self.scene.removeItem(vtx)
             for vtx in self.profile[profile_index]['markers']['vertex']]
            # clear list of vertex rubberbands
            self.profile[profile_index]['markers']['vertex'] = []

            #   - tieline
            # reset tieline rubberbands (delete from canvas)
            [tie.reset() and self.scene.removeItem(tie)
             for tie in self.profile[profile_index]['markers']['tieline']]
            # clear list of tieline rubberbands
            self.profile[profile_index]['markers']['tieline'] = []

            self.reset_sampling_points()
            self.reset_sampling_areas()
        except Exception:
            pass

        self.terminated = False

    # def canvasReleaseEvent(self, event):
    #     pt = event.mapPoint()
    #
    #     if event.button() == Qt.RightButton:
    #         if self.terminated is False:
    #             self.terminated = True
    #             self.addVertex(pt, True)
    #             self.proflineterminated.emit()
    #             return
    #     if self.terminated is True:
    #         self.resetProfileLine()
    #     self.profile_lines[self.profile_line_index].addPoint(pt, True)
    #     # clear list
    #     self.profile[profile_index]['markers']['tieline'] = []

    def add_point(self, point, end_point=False, profile_index=None):
        if profile_index is None:
            profile_index = self.profile_line_index

        # add coordinates
        self.profile[profile_index]['point'].append(point)

        rb = self.profile[profile_index]['markers']

        # add rubberband line
        # if not end_point:
        rb['line'].addPoint(point, True)

        # add rubberband vertex with icon shape
        vtx = self.get_vertex_rb(profile_index, point, end_point)
        rb['vertex'].append(vtx)

    def terminate_profile(self, pt=None):
        if pt:
            # add end-point vertex
            self.add_point(pt, end_point=True,
                           profile_index=self.profile_line_index)
        # emit terminated event
        self.proflineterminated.emit()
        # set teminaetd status
        self.terminated = True
        return

    # def initProfileLine(self, n_profile_line=2):
    #
    #     for idx in range(n_profile_line):
    #         # create new rubberband
    #         rb = QgsRubberBand(self.canvas, True)  # False = not a polygon
    #
    #         # set rubberband properties
    #         rb.setWidth(2)
    #         rb.setIcon(QgsRubberBand.ICON_CIRCLE)
    #         rb.setColor(self.plColor[idx])
    #
    #         # add rubberband to profile_lines
    #         self.profile_lines.append(rb)
    #
    #         self.vertices.append([])
    #         self.tieLines.append([])
    #
    #     # set current profile line to the first one (Profile Line 1)
    #     self.update_current_profile_line(0)

    def get_current_profile_line(self):
        return self.profile_line_index

    def update_current_profile_line(self, pIndex):
        """update index of profile line"""
        self.profile_line_index = pIndex

    def canvasPressEvent(self, event):
        pass

    # def canvasMoveEvent_old(self, event):
    #     if self.terminated is False and self.profile_line_index >= 0:
    #         plen = self.profile_lines[self.profile_line_index].numberOfVertices(
    #         )
    #         if plen > 0:
    #             pt = event.mapPoint()
    #             self.profile_lines[self.profile_line_index].movePoint(
    #                 plen - 1, pt)

    def canvasMoveEvent(self, event):
        if self.terminated:
            return
        rb_line = self.profile[self.profile_line_index]['markers']['line']
        plen = rb_line.numberOfVertices()
        if plen > 0:
            pt = event.mapPoint()
            rb_line.movePoint(plen - 1, pt)
        return

    def canvasReleaseEvent(self, event):

        if self.flag_double_clicked:
            self.flag_double_clicked = False
            return

        pt = event.mapPoint()

        if event.button() == Qt.RightButton and self.terminated is False:
            # right button click (termination)
            self.terminate_profile(pt)
            return

        if self.terminated is True:
            # first point
            # delete previous profile line
            self.reset_profile(self.profile_line_index)

        self.add_point(pt)

    def canvasDoubleClickEvent(self, event):
        self.flag_double_clicked = True
        self.reset_profile(self.profile_line_index)
        self.terminate_profile()
        return

    def get_all_profile_points(self):
        pts = []
        for idx in range(len(self.profile)):
            pts.append(self.get_profile_points(idx))
        return pts

    def get_profile_points(self, profile_index=None):
        if profile_index is None:
            profile_index = self.profile_line_index
        return [[pt.x(), pt.y()] for pt in self.profile[profile_index]['point']]

    def hide_profile_line(self):
        self.profile_line_points = self.get_all_profile_points()
        self.reset_all_profile()

    def show_profile_line(self):
        if sum([len(p) for p in self.profile_line_points]) == 0:
            return

        profile_line_index_original = self.profile_line_index
        i = 0
        for points in self.profile_line_points:
            self.profile_line_index = i
            if len(points):
                self.draw_profileLine_from_points(points)
            i += 1
        self.profile_line_points = []
        self.profile_line_index = profile_line_index_original

    def draw_tieline(self, pts):
        self.reset_tielines()
        myColor = [
            QColor(255, 255, 100, 200),  # Profile Line 1
            QColor(100, 255, 255, 200)  # Profile Line 2
        ]
        for pIndex in range(len(pts)):
            color = myColor[pIndex]
            color.setAlpha(150)
            for pt in pts[pIndex]:
                tl = QgsRubberBand(self.canvas, True)
                tl.setWidth(1)
                tl.setColor(color)
                tl.addPoint(QgsPointXY(*pt[0]), True)
                tl.addPoint(QgsPointXY(*pt[1]), True)
                self.profile[pIndex]['markers']['tieline'].append(tl)

    def init_tracking_marker(self):
        """create a trace marker on profile line"""
        self.tracking_marker = QgsVertexMarker(self.canvas)
        self.tracking_marker.setIconSize(10)
        self.tracking_marker.setPenWidth(3)
        self.tracking_marker.setIconType(QgsVertexMarker.ICON_CIRCLE)
        self.tracking_marker.setFillColor(QColor(0, 255, 0, 200))  # white
        self.tracking_marker.setColor(QColor(255, 255, 255, 200))  # white
        self.tracking_marker.setCenter(QgsPointXY(0, 0))
        self.tracking_marker.hide()

    def show_tracking_marker(self):
        if self.tracking_marker:
            self.tracking_marker.show()

    def hide_tracking_marker(self):
        if self.tracking_marker:
            self.tracking_marker.hide()

    def update_tracking_marker(self, pt):
        # self.trace_marker.movePoint(QgsPointXY(*pt))
        self.tracking_marker.setCenter(QgsPointXY(*pt))

    def reset_tracking_marker(self):
        if self.tracking_marker:
            # self.tracking_marker.reset()
            self.scene.removeItem(self.tracking_marker)
            self.tracking_marker = None

    def get_base_sampling_point_vertex_marker(self, color=None, pt=None):
        """return vertex for sampling point; color and position are option
        color [option]: QColor object
        pt [option]: QgsPointXY
        """

        my_size = 5
        my_icon_type = QgsVertexMarker.ICON_CIRCLE
        qvm = QgsVertexMarker(self.canvas)
        qvm.setIconType(my_icon_type)
        qvm.setIconSize(my_size)
        if color:
            qvm.setFillColor(color)
            qvm.setColor(color)
        if pt:
            qvm.setCenter(pt)

        return qvm

    def get_vertex_rb(self, profile_index, point, end_point=False):
        """return vertex rubberband with given params"""
        icon = QgsRubberBand.ICON_FULL_BOX if end_point else QgsRubberBand.ICON_CIRCLE

        vtx = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        vtx.setIconSize(10)
        vtx.setIcon(icon)
        vtx.setColor(self.plColor[profile_index])
        vtx.addPoint(QgsPointXY(*point), True)

        return vtx

    def draw_profileLine_from_points(self, points):
        self.reset_profile(self.profile_line_index)

        if len(points) == 0:
            return

        points = [QgsPointXY(*p) for p in points]
        # add points except last point
        [self.add_point(p) for p in points[:-1]]
        # add last point
        self.terminate_profile(points[-1])

    def add_sampling_areas(self, profile_index, pts, color=None):
        if color is None:
            color = QColor(255, 30, 30)
        myColor = QColor(color)
        myColor.setAlpha(35)
        for pt in pts:
            rb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
            rb.addPoint(QgsPointXY(*pt[0]))
            rb.addPoint(QgsPointXY(*pt[1]))
            rb.addPoint(QgsPointXY(*pt[3]))
            rb.addPoint(QgsPointXY(*pt[2]))
            rb.addPoint(QgsPointXY(*pt[0]))
            rb.setColor(myColor)
            rb.setWidth(2)
            self.profile[profile_index]['markers']['sampling_area'].append(rb)

    def add_sampling_points(self, profile_index, pts, color=None):
        """ add sampling point markers to the canvas """

        if not profile_index:
            profile_index = self.profile_line_index

        if color is None:
            color = QColor(255, 0, 0)  # Red (default)

        my_color = QColor(color)
        my_color.setAlpha(100)
        for pt in pts:  # scan d (vertical)
            for p1 in pt:  # scan within same d (horizontal)
                qpt = QgsPointXY(*p1)
                vm = self.get_base_sampling_point_vertex_marker(my_color, qpt)
                self.profile[profile_index]['markers']['sampling_point'].append(
                    vm)

    def reset_sampling_points(self, profile_index=None):
        if profile_index is None:
            profile_index = self.profile_line_index
        [self.scene.removeItem(
            pt) for pt in self.profile[profile_index]['markers']['sampling_point']]
        self.profile[profile_index]['markers']['sampling_point'] = []

    def reset_sampling_areas(self, profile_index=None):
        if profile_index is None:
            profile_index = self.profile_line_index
        [rect.reset() and self.scene.removeItem(rect)
         for rect in self.profile[profile_index]['markers']['sampling_area']]
        self.profile[profile_index]['markers']['sampling_area'] = []

    def reset_tielines(self, profile_index=None):
        if profile_index is None:
            profile_index = self.profile_line_index
        [tie.reset() and self.scene.removeItem(tie)
         for tie in self.profile[profile_index]['markers']['tieline']]
        self.profile[profile_index]['markers']['tieline'] = []
