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

    core.QgsPointXY = QgsPointXY
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

