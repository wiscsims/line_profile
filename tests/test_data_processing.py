import unittest

from tests.qgis_stubs import install

install()

from tools.dataProcessingTool import DataProcessingTool


class IdentifyResult:
    def __init__(self, results, valid=True):
        self._results = results
        self._valid = valid

    def isValid(self):
        return self._valid

    def results(self):
        return self._results


class Provider:
    def __init__(self, result):
        self.result = result

    def identify(self, point, identify_format):
        return self.result


class CoordinateProvider:
    def identify(self, point, identify_format):
        return IdentifyResult({1: point.x()})


class RasterLayer:
    def dataProvider(self):
        return CoordinateProvider()

    def rasterUnitsPerPixelX(self):
        return 1

    def rasterUnitsPerPixelY(self):
        return 2


class PointGeometry:
    def __init__(self, point):
        self.point = point

    def asPoint(self):
        return self.point


class VectorFeature:
    def __init__(self, point, value):
        self._geometry = PointGeometry(point)
        self.values = {"value": value}

    def attribute(self, field):
        return self.values[field]

    def geometry(self):
        return self._geometry

    def __setitem__(self, field, value):
        self.values[field] = value


class VectorProvider:
    def __init__(self, has_distance_field=False):
        self.has_distance_field = has_distance_field

    def fieldNameIndex(self, name):
        return 0 if self.has_distance_field and name == "distance" else -1


class VectorLayer:
    def __init__(self, feature, has_distance_field=False):
        self.feature = feature
        self.provider = VectorProvider(has_distance_field)
        self.updated = 0

    def dataProvider(self):
        return self.provider

    def selectedFeatureCount(self):
        return 0

    def getFeatures(self):
        return [self.feature]

    def id(self):
        return "vector"

    def updateFeature(self, feature):
        self.updated += 1

    def startEditing(self):
        pass

    def commitChanges(self):
        pass


class DataProcessingToolTest(unittest.TestCase):
    def setUp(self):
        self.tool = DataProcessingTool(2)

    def profile(self, start, end):
        return self.tool.getProfileLines([start, end])

    def test_horizontal_projection_preserves_x_in_both_directions(self):
        for start, end in (([0, 20], [200, 20]), ([200, 20], [0, 20])):
            line = self.profile(start, end)
            self.assertEqual(self.tool.getProjectedPoint(line, [100, 50], 100), [100, 20, 0])
            self.assertEqual(self.tool.getProjectedPoint(line, [100, -10], 100), [100, 20, 0])

    def test_projection_outside_segment_and_distance_limit(self):
        line = self.profile([0, 20], [200, 20])
        self.assertFalse(self.tool.getProjectedPoint(line, [250, 50], 100))
        self.assertFalse(self.tool.getProjectedPoint(line, [100, 50], 20))

    def test_vertical_and_diagonal_projection(self):
        vertical = self.profile([10, 0], [10, 100])
        self.assertEqual(self.tool.getProjectedPoint(vertical, [20, 50], 100), [10, 50, 0])
        diagonal = self.profile([0, 0], [100, 100])
        projected = self.tool.getProjectedPoint(diagonal, [100, 0], 100)
        self.assertAlmostEqual(projected[0], 50)
        self.assertAlmostEqual(projected[1], 50)

    def test_distance_to_coordinates_clamps_and_handles_boundaries(self):
        lines = self.tool.getProfileLines([[0, 0], [10, 0], [10, 10]])
        self.assertEqual(self.tool.getCurrentCoordinates(lines, -1), [0, 0])
        self.assertEqual(self.tool.getCurrentCoordinates(lines, 5), [5, 0])
        self.assertEqual(self.tool.getCurrentCoordinates(lines, 10), [10, 0])
        self.assertEqual(self.tool.getCurrentCoordinates(lines, 10.5), [10, 0.5])
        self.assertEqual(self.tool.getCurrentCoordinates(lines, 20), [10, 10])
        self.assertEqual(self.tool.getCurrentCoordinates(lines, 25), [10, 10])

    def test_distance_to_coordinates_reversed_and_empty(self):
        lines = self.profile([10, 10], [0, 0])
        self.assertEqual(self.tool.getCurrentCoordinates(lines, 0), [10, 10])
        self.assertEqual(self.tool.getCurrentCoordinates(lines, self.tool.sumD(lines)), [0, 0])
        self.assertIsNone(self.tool.getCurrentCoordinates([], 1))

    def test_sort_data_is_stable_and_does_not_mutate_inputs(self):
        x = [3, 1, 1, 2]
        y = [30, 10, 11, 20]
        self.assertEqual(self.tool.sortDataByX(x, y), ([1, 1, 2, 3], [10, 11, 20, 30]))
        self.assertEqual(x, [3, 1, 1, 2])
        self.assertEqual(y, [30, 10, 11, 20])
        self.assertEqual(self.tool.sortDataByX([], []), ([], []))
        self.assertEqual(self.tool.sortDataByX([1], [2]), ([1], [2]))

    def test_nodata_and_identify_failures_are_missing(self):
        self.assertEqual(self.tool.getPointValue(Provider(IdentifyResult({1: 12})), None, 1), 12)
        self.assertIsNone(self.tool.getPointValue(Provider(IdentifyResult({1: None})), None, 1))
        self.assertIsNone(self.tool.getPointValue(Provider(IdentifyResult({})), None, 1))
        self.assertIsNone(self.tool.getPointValue(Provider(IdentifyResult({1: 12}, valid=False)), None, 1))

    def test_missing_value_average(self):
        self.assertEqual(self.tool.averageValidValues([10, None, 20]), 15)
        self.assertIsNone(self.tool.averageValidValues([None, None]))

    def test_duplicate_adjacent_vertices_are_skipped(self):
        lines = self.tool.getProfileLines([[0, 0], [0, 0], [10, 0]])
        self.assertEqual(len(lines), 1)

    def test_raster_profile_stores_one_center_per_sample(self):
        lines = self.profile([0, 0], [2, 0])
        x, y = self.tool.getRasterProfile(lines, RasterLayer(), "Band 1", False, "raster", 0, 0)
        centers = self.tool.get_profile_sample_centers(0, "raster")
        self.assertEqual(x, [0, 1, 2])
        self.assertEqual(y, [0, 1, 2])
        self.assertEqual([(point.x(), point.y()) for point in centers], [(0, 0), (1, 0), (2, 0)])

    def test_raster_distance_is_scaled_once(self):
        self.tool.pixel_size = 2
        lines = self.profile([0, 0], [2, 0])
        x, _ = self.tool.getRasterProfile(lines, RasterLayer(), "Band 1", False, "raster", 0, 0)
        self.assertEqual(x, [0, 2, 4])

    def test_vector_distance_is_scaled_once_and_read_only_profile_does_not_edit(self):
        self.tool.pixel_size = 2
        lines = self.profile([0, 0], [10, 0])
        feature = VectorFeature([5, 1], 7)
        layer = VectorLayer(feature)
        x, y = self.tool.getVectorProfile(lines, layer, "value", 100, None, 0)
        self.assertEqual((x, y), ([10], [7]))
        self.assertEqual(layer.updated, 0)

    def test_vector_distance_field_is_written_when_requested(self):
        lines = self.profile([0, 0], [10, 0])
        feature = VectorFeature([5, 1], 7)
        layer = VectorLayer(feature, has_distance_field=True)
        self.tool.getVectorProfile(lines, layer, "value", 100, "distance", 0)
        self.assertEqual(feature.values["distance"], 5)
        self.assertEqual(layer.updated, 1)


if __name__ == "__main__":
    unittest.main()
