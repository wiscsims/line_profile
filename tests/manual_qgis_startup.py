"""Prepare an isolated, interactive Line Profile test session in QGIS."""

import os
import traceback

import numpy as np
from osgeo import gdal, osr

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsSettings,
    QgsVectorLayer,
)
import qgis.utils


TEST_ROOT = "/private/tmp/line-profile-qgis-manual"
STATUS_PATH = os.path.join(TEST_ROOT, "startup-status.txt")
def write_status(message):
    os.makedirs(TEST_ROOT, exist_ok=True)
    with open(STATUS_PATH, "w", encoding="utf-8") as status_file:
        status_file.write(message + "\n")


def create_test_raster(path):
    width = 256
    height = 128
    x_values = np.arange(width, dtype=np.float32)
    profile = (
        80.0
        + 28.0 * np.sin(x_values / 8.0)
        + 12.0 * np.sin(x_values / 2.7)
        + 35.0 * np.exp(-((x_values - 55.0) / 7.0) ** 2)
        + 45.0 * np.exp(-((x_values - 185.0) / 10.0) ** 2)
    )
    raster = np.tile(profile, (height, 1))
    raster += np.linspace(-6.0, 6.0, height, dtype=np.float32)[:, None]
    raster[:, 122:126] = -9999.0

    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(path, width, height, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((0.0, 1.0, 0.0, 128.0, 0.0, -1.0))
    spatial_reference = osr.SpatialReference()
    spatial_reference.ImportFromEPSG(3857)
    dataset.SetProjection(spatial_reference.ExportToWkt())
    band = dataset.GetRasterBand(1)
    band.WriteArray(raster)
    band.SetNoDataValue(-9999.0)
    band.FlushCache()
    dataset.FlushCache()
    dataset = None


def create_test_points():
    layer = QgsVectorLayer("Point?crs=EPSG:3857", "Line Profile Vector Test Points", "memory")
    provider = layer.dataProvider()
    provider.addAttributes([QgsField("value", QVariant.Double)])
    layer.updateFields()
    features = []
    for x_value in range(16, 248, 16):
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x_value, 64 + ((x_value // 16) % 3 - 1) * 5)))
        feature.setAttributes([float(30 + (x_value % 70))])
        features.append(feature)
    provider.addFeatures(features)
    layer.updateExtents()
    return layer


def load_line_profile_plugin():
    settings = QgsSettings()
    settings.setValue("PythonPlugins/line_profile", True)
    qgis.utils.updateAvailablePlugins()
    if "line_profile" not in qgis.utils.available_plugins:
        raise RuntimeError(
            "line_profile was not discovered. QGIS_PLUGINPATH={}".format(
                os.environ.get("QGIS_PLUGINPATH", "")
            )
        )
    if "line_profile" in qgis.utils.plugins:
        return qgis.utils.plugins["line_profile"]
    if not qgis.utils.loadPlugin("line_profile"):
        raise RuntimeError("QGIS could not load the line_profile plugin")
    if not qgis.utils.startPlugin("line_profile"):
        raise RuntimeError("QGIS could not start the line_profile plugin")
    return qgis.utils.plugins["line_profile"]


def prepare_manual_test():
    qgis_iface = qgis.utils.iface
    try:
        os.makedirs(TEST_ROOT, exist_ok=True)
        raster_path = os.path.join(TEST_ROOT, "line-profile-test.tif")
        create_test_raster(raster_path)

        project = QgsProject.instance()
        project.clear()
        raster_layer = QgsRasterLayer(raster_path, "Line Profile Peak Valley Test Raster")
        if not raster_layer.isValid():
            raise RuntimeError("The generated GeoTIFF is not a valid QGIS raster layer")
        point_layer = create_test_points()
        project.addMapLayer(raster_layer)
        project.addMapLayer(point_layer)
        qgis_iface.mapCanvas().setLayers([point_layer, raster_layer])
        qgis_iface.setActiveLayer(raster_layer)
        qgis_iface.mapCanvas().setExtent(raster_layer.extent())
        qgis_iface.mapCanvas().refresh()
        QApplication.processEvents()

        plugin = load_line_profile_plugin()
        plugin.run()
        if plugin.model.rowCount() == 0:
            plugin.model.addElement(raster_layer, "Band 1")
        plugin.model.updateFlag = True
        plugin.profileLineTool.draw_profileLine_from_points([[8.0, 64.0], [248.0, 64.0]])
        plugin.updatePlot()
        plugin.dock.raise_()
        plugin.dock.activateWindow()

        message = (
            "READY: Line Profile loaded with a raster, vector test points, and a horizontal profile. "
            "Use the Peak / Valley Detection panel, then Clear the profile to test manual drawing. "
            "data_sources={}, profile_points={}.".format(
                plugin.dock.Cmb_PeakDataSource.count(),
                [len(points) for points in plugin.profileLineTool.get_all_profile_points()],
            )
        )
        write_status(message)
        qgis_iface.messageBar().pushSuccess("Line Profile manual test", message)
    except Exception:
        diagnostic = traceback.format_exc()
        write_status("FAILED\n" + diagnostic)
        qgis_iface.messageBar().pushCritical("Line Profile manual test failed", diagnostic.splitlines()[-1])
        raise


write_status("STARTING")
prepare_manual_test()
