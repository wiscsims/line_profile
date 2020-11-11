from functools import reduce

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsPointXY, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand


class ProfileLineTool(QgsMapTool):

    doubleClicked = pyqtSignal()
    proflineterminated = pyqtSignal()

    canvasClicked = pyqtSignal('QgsPointXY')
    canvasClickedRight = pyqtSignal('QgsPointXY')
    canvasDoubleClicked = pyqtSignal('QgsPointXY')
    canvasMoved = pyqtSignal('QgsPointXY')

    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas

        self.scene = self.canvas.scene()
        self.terminated = True
        self.profile_line_index = 1
        self.profile_lines = []

        self.profile_line_points = []

        self.profile = []
        """
         data structure of each profile line
         {
           'point': [QgsPointXY()-1], [QgsPointXY()-2], ...],
           'rubberband': {
                'line': rb_line,
                'vertex': [rb_vertex1, rb_vertex2, ...],
                'tieline': [rb_tieline1, rb_tieline2, ...],
                'raster_sampling_area': [rb_sampling_area1, rb_sampling_area2, ...],
                'raster_sampling_point': [rb_sampling_point1, rb_sampling_point2, ...],
           }
         }
        """

        self.rbR = QgsRubberBand(canvas, True)  # False = not a polygon
        self.rbR.setWidth(2)
        self.rbR.setColor(QColor(255, 20, 20, 150))
        self.rbR.setIcon(QgsRubberBand.ICON_CIRCLE)

        self.tieLines = []
        self.vertices = []
        self.rasterPoint = []
        self.samplingRange = []

        self.plColor = [QColor(255, 20, 20, 250),
                        QColor(20, 20, 255, 250),
                        QColor(20, 255, 20, 250)]

        self.flag_double_clicked = False

        # print('INIT PROFILELINETOOL')

    def get_default_profile(self, idx=0):
        # set rubberband properties
        # False = not a polygon
        rb_line = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        rb_line.setWidth(1)
        rb_line.setIcon(QgsRubberBand.ICON_CIRCLE)
        rb_line.setColor(self.plColor[idx])

        default_profile = {
            'point': [],
            'rubberband': {
                'line': rb_line,
                'vertex': [],
                'tieline': [],
                'raster_sampling_area': [],
                'raster_sampling_point': []
            }
        }

        return default_profile

    def init_profile(self, n_profile_line):
        for profile_index in range(n_profile_line):
            default_profile = self.get_default_profile(profile_index)
            self.profile.append(default_profile)

    def reset_all_profile(self):
        n_profile = len(self.profile)
        for i in range(n_profile):
            self.reset_profile(i)

    def reset_profile(self, profile_index):
        # reset points
        self.profile[profile_index]['point'] = []

        # reset rubberband
        #   - line
        self.profile[profile_index]['rubberband']['line'].reset()

        try:
            #   - vertex
            # reset vertex rubberbands (delete from canvas)
            [vtx.reset() and self.scene.removeItem(vtx)
             for vtx in self.profile[profile_index]['rubberband']['vertex']]
            # clear list of vertex rubberbands
            self.profile[profile_index]['rubberband']['vertex'] = []

            #   - tieline
            # reset tieline rubberbands (delete from canvas)
            [tie.reset() and self.scene.removeItem(tie)
             for tie in self.profile[profile_index]['rubberband']['tieline']]
            # clear list of tieline rubberbands
            self.profile[profile_index]['rubberband']['tieline'] = []

            self.reset_raster_sampling_points()
            self.reset_raster_sampling_area()
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
    #     self.profile[profile_index]['rubberband']['tieline'] = []

    def add_point(self, point, end_point=False, profile_index=None):
        if profile_index is None:
            profile_index = self.profile_line_index

        # add coordinates
        self.profile[profile_index]['point'].append(point)

        rb = self.profile[profile_index]['rubberband']

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

    def initProfileLine(self, n_profile_line=2):

        for idx in range(n_profile_line):
            # create new rubberband
            rb = QgsRubberBand(self.canvas, True)  # False = not a polygon

            # set rubberband properties
            rb.setWidth(2)
            rb.setIcon(QgsRubberBand.ICON_CIRCLE)
            rb.setColor(self.plColor[idx])

            # add rubberband to profile_lines
            self.profile_lines.append(rb)

            self.vertices.append([])
            self.tieLines.append([])

        # set current profile line to the first one (Profile Line 1)
        self.changeProfileLine(0)

    def getCurrentProfileLine(self):
        return self.profile_line_index

    def changeProfileLine(self, pIndex):
        """change index of profile line"""
        self.profile_line_index = pIndex

    def canvasPressEvent(self, event):
        pass

    def canvasMoveEvent_old(self, event):
        if self.terminated is False and self.profile_line_index >= 0:
            plen = self.profile_lines[self.profile_line_index].numberOfVertices(
            )
            if plen > 0:
                pt = event.mapPoint()
                self.profile_lines[self.profile_line_index].movePoint(
                    plen - 1, pt)

    def canvasMoveEvent(self, event):
        if self.terminated is False:
            rb_line = self.profile[self.profile_line_index]['rubberband']['line']
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

    def canvasReleaseEvent_old(self, event):
        pt = event.mapPoint()

        if event.button() == Qt.RightButton:
            if self.terminated is False:
                self.terminated = True
                self.addVertex(pt, True)
                self.proflineterminated.emit()
                return
        if self.terminated is True:
            self.resetProfileLine()
        self.profile_lines[self.profile_line_index].addPoint(pt, True)
        self.addVertex(pt)

    def canvasDoubleClickEvent(self, event):
        self.flag_double_clicked = True
        self.reset_profile(self.profile_line_index)
        self.terminate_profile()
        return
        #
        # pt = event.mapPoint()
        # self.canvasDoubleClicked.emit(pt)
        #
        # self.resetProfileLine()
        # self.doubleClicked.emit()
        # self.emit(SIGNAL('doubleClicked'))

    def updateProfileLine(self):
        pass
        return
        # pt = self.getProfPoints()
        # self.rb.reset()
        # self.resetVertices()
        # ptLast = pt.pop()
        # for p in pt:
        #     point = QgsPointXY(p[0], p[1])
        #     self.rb.addPoint(point, True)
        #     self.addVertex(point)
        # point = QgsPointXY(ptLast[0], ptLast[1])
        # self.rb.addPoint(point, True)
        # self.addVertex(point, True)
        # self.terminated = True

    def get_all_profile_points(self):
        pts = []
        for p in self.profile:
            pts.append([[pt.x(), pt.y()] for pt in p['point']])
        return pts

    def getAllProfPoints(self):
        profVtx = []
        if self.profile_line_index == -1:
            return profVtx
        for r in self.profile_lines:
            vtx = []
            n = r.numberOfVertices()
            for i in range(n):
                pt = r.getPoint(0, i)
                vtx.append([pt.x(), pt.y()])
            # if len(vtx):
            profVtx.append(vtx)
        return profVtx

    def getProfPoints(self):
        # [[x0, y0], [x1, y1], [x2, y2],. ., [xn, yn]]
        profVertices = []
        if self.profile_line_index == -1:
            return profVertices

        n = self.profile_lines[self.profile_line_index].numberOfVertices()
        for i in range(n):
            pt = self.profile_lines[self.profile_line_index].getPoint(0, i)
            # check duplicated points
            current_pt = [pt.x(), pt.y()]
            if profVertices[-1] == current_pt:
                continue
            profVertices.append(current_pt)
        return profVertices

    def hideProfileLine(self):
        self.profile_line_points = self.getAllProfPoints()
        self.profile_line_points = self.get_all_profile_points()
        self.reset_all_profile()
        # self.resetProfileLine(True)

    def hide_profile_line(self):
        # print('hide_profile_line')
        self.profile_line_points = self.get_all_profile_points()
        self.reset_all_profile()

    def show_profile_line(self):
        # print('show_profile_line')
        if sum([len(p) for p in self.profile_line_points]) == 0:
            # print('no hidden profile lines')
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

    def showProfileLine(self):
        if len(self.profile_line_points) == 0:
            return
        i = 0
        profile_line_index_original = self.profile_line_index
        for points in self.profile_line_points:
            self.profile_line_index = i
            self.drawProfileLineFromPoints(points)
            i += 1
        self.profile_line_points = []
        self.profile_line_index = profile_line_index_original

    def resetProfileLine(self, all=False):
        if all:
            [myRb.reset() for myRb in self.profile_lines]
        else:
            self.profile_lines[self.profile_line_index].reset()
        self.rbR.reset()
        self.resetTieLines(all)
        self.resetVertices(all)
        self.resetRasterPoints()
        self.resetSamplingRange()
        self.terminated = False

    def drawTieLine(self, pts):
        self.resetTieLines(True)
        self.reset_tielines()
        myColor = [QColor(255, 255, 100, 200), QColor(100, 255, 255, 200)]
        for pIndex in range(len(pts)):
            color = myColor[pIndex]
            color.setAlpha(150)
            self.tieLines.append([])
            for pt in pts[pIndex]:
                tl = QgsRubberBand(self.canvas, True)
                tl.setWidth(1)
                tl.setColor(color)
                tl.addPoint(QgsPointXY(pt[0][0], pt[0][1]), True)
                tl.addPoint(QgsPointXY(pt[1][0], pt[1][1]), True)
                self.profile[pIndex]['rubberband']['tieline'].append(tl)

    def drawTieLine2(self, pt1, pt2):
        tl = QgsRubberBand(self.canvas, True)
        tl.setWidth(1)
        tl.setColor(QColor(255, 255, 100, 200))
        tl.addPoint(QgsPointXY(pt1[0], pt1[1]), True)
        tl.addPoint(QgsPointXY(pt2[0], pt2[1]), True)
        self.tieLines.append(tl)

    def resetTieLines(self, all=False):
        if self.profile_line_index < 0 or reduce(lambda x, y: x + len(y), self.tieLines, 0) == 0:
            return
        if all:
            for pIndex in range(len(self.tieLines)):
                [tl.reset() for tl in self.tieLines[pIndex]]
                [self.canvas.scene().removeItem(tl)
                 for tl in self.tieLines[pIndex]]
            self.tieLines = []
        else:
            [tl.reset() for tl in self.tieLines[self.profile_line_index]]
            [self.canvas.scene().removeItem(tl)
             for tl in self.tieLines[self.profile_line_index]]

    def addVertex2(self, pt1):
        tl = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        tl.setIconSize(5)
        tl.setIcon(QgsRubberBand.ICON_CIRCLE)
        tl.setColor(QColor(255, 255, 255, 200))
        tl.addPoint(QgsPointXY(pt1[0], pt1[1]), True)
        self.rasterPoint.append(tl)

    def addSamplingRange(self, pt1, terminator=False):
        if terminator:
            icon = QgsRubberBand.ICON_FULL_BOX
        else:
            icon = QgsRubberBand.ICON_CIRCLE
        tl = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        tl.setIconSize(3)
        # tl.setWidth(5)
        tl.setIcon(icon)
        tl.setColor(QColor(255, 255, 220, 200))
        tl.addPoint(QgsPointXY(pt1[0], pt1[1]), True)
        self.samplingRange.append(tl)

    def addSamplingArea(self, pts, color):
        myColor = QColor(color)
        myColor.setAlpha(35)
        for pt in pts:
            rb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
            rb.addPoint(QgsPointXY(pt[0][0], pt[0][1]))
            rb.addPoint(QgsPointXY(pt[1][0], pt[1][1]))
            rb.addPoint(QgsPointXY(pt[3][0], pt[3][1]))
            rb.addPoint(QgsPointXY(pt[2][0], pt[2][1]))
            rb.addPoint(QgsPointXY(pt[0][0], pt[0][1]))
            rb.setColor(myColor)
            rb.setWidth(2)
            self.profile[self.profile_line_index]['rubberband']['raster_sampling_area'].append(
                rb)

    def addSamplingRange2(self, pts, color):
        myColor = QColor(color)
        myColor.setAlpha(200)
        mySize = 3
        for pt1 in pts:
            qpt = QgsPointXY(pt1[0], pt1[1])
            tl2 = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
            tl2.addPoint(qpt, True)
            tl2.setIconSize(mySize)
            tl2.setIcon(QgsRubberBand.ICON_CIRCLE)
            tl2.setColor(myColor)
            self.profile[self.profile_line_index]['rubberband']['raster_sampling_point'].append(
                tl2)

    def get_vertex_rb(self, profile_index, point, end_point=False):
        """return vertex rubberband with given params"""
        icon = QgsRubberBand.ICON_FULL_BOX if end_point else QgsRubberBand.ICON_CIRCLE

        vtx = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        vtx.setIconSize(10)
        vtx.setIcon(icon)
        vtx.setColor(self.plColor[profile_index])
        vtx.addPoint(QgsPointXY(*point), True)

        return vtx

    def addVertex(self, pt1, terminator=False):
        if terminator:
            icon = QgsRubberBand.ICON_FULL_BOX
        else:
            icon = QgsRubberBand.ICON_CIRCLE
        rb_profileline = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        rb_profileline.setIconSize(10)
        rb_profileline.setIcon(icon)
        rb_profileline.setColor(self.plColor[self.profile_line_index])
        rb_profileline.addPoint(QgsPointXY(pt1[0], pt1[1]), True)

        self.vertices[self.profile_line_index].append(rb_profileline)

    def draw_profileLine_from_points(self, points):
        points = [QgsPointXY(*p) for p in points]
        [self.add_point(p) for p in points[:-1]]
        self.terminate_profile(points[-1])

    def drawProfileLineFromPoints(self, points):
        # points = points[self.profile_line_index]
        self.resetProfileLine()
        num = len(points)

        if not num:
            # no profileline
            # print('no profile line')
            return

        points = [QgsPointXY(p[0], p[1]) for p in points]
        i = 0
        # print('self.profile_line_index: ', self.profile_line_index)
        # print('i: ', i)
        for i in range(num - 1):
            self.profile_lines[self.profile_line_index].addPoint(
                points[i], True)
            self.addVertex(points[i])
        self.terminated = True
        self.profile_lines[self.profile_line_index].addPoint(
            points[i + 1], True)
        self.addVertex(points[i + 1], True)

    def resetVertices(self, full=False):
        if full:
            for vtx in self.vertices:
                [v.reset() for v in vtx]
            for vtx in self.vertices:
                [self.canvas.scene().removeItem(v) for v in vtx]
            self.vertices = []
        else:
            try:
                [tl.reset() for tl in self.vertices[self.profile_line_index]]
                [self.canvas.scene().removeItem(tl)
                 for tl in self.vertices[self.profile_line_index]]
            except Exception:
                pass

    def reset_raster_sampling_points(self, profile_index=None):
        if profile_index is None:
            profile_index = self.profile_line_index
        #   - raster sampling area (rectangle) and sampling point
        [pt.reset() and self.scene.removeItem(pt)
         for pt in self.profile[profile_index]['rubberband']['raster_sampling_point']]
        self.profile[profile_index]['rubberband']['raster_sampling_point'] = []

    def reset_raster_sampling_area(self, profile_index=None):
        if profile_index is None:
            profile_index = self.profile_line_index
        [rect.reset() and self.scene.removeItem(rect)
         for rect in self.profile[profile_index]['rubberband']['raster_sampling_area']]
        self.profile[profile_index]['rubberband']['raster_sampling_area'] = []

    def reset_tielines(self, profile_index=None):
        if profile_index is None:
            profile_index = self.profile_line_index
        [tie.reset() and self.scene.removeItem(tie)
         for tie in self.profile[profile_index]['rubberband']['tieline']]
        self.profile[profile_index]['rubberband']['tieline'] = []

    def resetRasterPoints(self):
        [tl.reset() for tl in self.rasterPoint]
        [self.canvas.scene().removeItem(tl) for tl in self.rasterPoint]
        self.rasterPoint = []

    def resetSamplingRange(self):
        [tl.reset() for tl in self.samplingRange]
        [self.canvas.scene().removeItem(tl) for tl in self.samplingRange]
        self.samplingRange = []
