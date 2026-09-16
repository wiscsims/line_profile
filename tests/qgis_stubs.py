"""Minimal QGIS stubs used by unit tests outside a QGIS installation."""

import sys
import types


def install():
    try:
        import qgis  # noqa: F401
        return
    except ImportError:
        pass

    qgis = types.ModuleType("qgis")
    core = types.ModuleType("qgis.core")
    gui = types.ModuleType("qgis.gui")
    pyqt = types.ModuleType("qgis.PyQt")
    qtcore = types.ModuleType("qgis.PyQt.QtCore")
    qtgui = types.ModuleType("qgis.PyQt.QtGui")

    class QgsPointXY:
        def __init__(self, x=0, y=0):
            if not isinstance(x, (int, float)):
                x, y = x
            self._x = x
            self._y = y

        def x(self):
            return self._x

        def y(self):
            return self._y

        def __iter__(self):
            return iter((self._x, self._y))

        def __eq__(self, other):
            return tuple(self) == tuple(other)

    class QgsRectangle:
        def __init__(self, xmin=0, ymin=0, xmax=0, ymax=0):
            self._xmin = xmin
            self._ymin = ymin
            self._xmax = xmax
            self._ymax = ymax

        def xMinimum(self):
            return self._xmin

        def yMinimum(self):
            return self._ymin

        def xMaximum(self):
            return self._xmax

        def yMaximum(self):
            return self._ymax

        def isEmpty(self):
            return self._xmax <= self._xmin or self._ymax <= self._ymin

    class QgsRaster:
        IdentifyFormatValue = 1

    class Qt:
        RightButton = 2

    class QColor:
        def __init__(self, *args):
            self.args = args

        def setAlpha(self, alpha):
            self.alpha = alpha

    class Signal:
        def connect(self, callback):
            self.callback = callback

        def disconnect(self, callback):
            return None

        def emit(self, *args):
            return None

    class QgsMapTool:
        def __init__(self, canvas=None):
            self.canvas = canvas

    class QgsRubberBand:
        ICON_CIRCLE = 1
        ICON_FULL_BOX = 2

        def __init__(self, *args):
            self.points = []

        def setWidth(self, *args):
            pass

        def setIcon(self, *args):
            pass

        def setIconSize(self, *args):
            pass

        def setColor(self, *args):
            pass

        def addPoint(self, point, *args):
            self.points.append(point)

        def reset(self):
            self.points = []

    class QgsVertexMarker:
        ICON_CIRCLE = 1

    class QgsWkbTypes:
        PointGeometry = 1
        LineGeometry = 2
        PolygonGeometry = 3

        @staticmethod
        def geometryType(wkb_type):
            return wkb_type

    class QgsGeometry:
        def __init__(self, kind="empty", value=None):
            self.kind = kind
            self.value = value

        @classmethod
        def fromPolylineXY(cls, points):
            return cls("line", list(points))

        @classmethod
        def fromRect(cls, rectangle):
            return cls("rectangle", rectangle)

        @classmethod
        def fromPointXY(cls, point):
            return cls("point", point)

        def isEmpty(self):
            return self.kind == "empty"

        def wkbType(self):
            if self.kind == "line":
                return QgsWkbTypes.LineGeometry
            if self.kind == "point":
                return QgsWkbTypes.PointGeometry
            if self.kind == "rectangle":
                return QgsWkbTypes.PolygonGeometry
            return 0

        def isMultipart(self):
            return False

        def asPolyline(self):
            return list(self.value) if self.kind == "line" else []

        def asMultiPolyline(self):
            return []

        def asGeometryCollection(self):
            return []

        def intersection(self, other):
            if self.kind != "line" or other.kind != "rectangle" or len(self.value) != 2:
                return QgsGeometry()
            start, end = self.value
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            rectangle = other.value
            p = (-dx, dx, -dy, dy)
            q = (
                start.x() - rectangle.xMinimum(),
                rectangle.xMaximum() - start.x(),
                start.y() - rectangle.yMinimum(),
                rectangle.yMaximum() - start.y(),
            )
            low, high = 0.0, 1.0
            for direction, distance in zip(p, q):
                if direction == 0:
                    if distance < 0:
                        return QgsGeometry()
                    continue
                ratio = distance / direction
                if direction < 0:
                    low = max(low, ratio)
                else:
                    high = min(high, ratio)
                if low > high:
                    return QgsGeometry()
            if high - low <= 1e-12:
                return QgsGeometry()
            return QgsGeometry.fromPolylineXY(
                [
                    QgsPointXY(start.x() + low * dx, start.y() + low * dy),
                    QgsPointXY(start.x() + high * dx, start.y() + high * dy),
                ]
            )

        def lineLocatePoint(self, point_geometry):
            if self.kind != "line" or point_geometry.kind != "point" or len(self.value) != 2:
                return -1
            start, end = self.value
            point = point_geometry.value
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            length_squared = dx * dx + dy * dy
            if length_squared == 0:
                return 0
            fraction = ((point.x() - start.x()) * dx + (point.y() - start.y()) * dy) / length_squared
            fraction = min(1.0, max(0.0, fraction))
            return (length_squared ** 0.5) * fraction

    core.QgsPointXY = QgsPointXY
    core.QgsRectangle = QgsRectangle
    core.QgsGeometry = QgsGeometry
    core.QgsRaster = QgsRaster
    core.NULL = object()
    core.QgsWkbTypes = QgsWkbTypes
    gui.QgsMapTool = QgsMapTool
    gui.QgsRubberBand = QgsRubberBand
    gui.QgsVertexMarker = QgsVertexMarker
    qtcore.Qt = Qt
    qtcore.pyqtSignal = lambda *args, **kwargs: Signal()
    qtgui.QColor = QColor

    sys.modules.update(
        {
            "qgis": qgis,
            "qgis.core": core,
            "qgis.gui": gui,
            "qgis.PyQt": pyqt,
            "qgis.PyQt.QtCore": qtcore,
            "qgis.PyQt.QtGui": qtgui,
        }
    )
