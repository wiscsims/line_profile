import unittest

from tests.qgis_stubs import install

install()

from qgis.core import QgsRectangle

from tools.dataProcessingTool import DataProcessingTool
from tools.detectionScope import detect_in_ranges, ranges_for_plot
from tools.peakDetectionTool import PeakDetectionTool
from tools.featurePointStore import FeaturePointStore
from tools.profileVisibility import profile_visible_ranges
from tools.rangeUtils import format_ranges, merge_ranges, parse_ranges


def fake_find_peaks(signal, prominence=None, width=None):
    signal = [float(value) for value in signal]
    indexes = [
        index
        for index in range(1, len(signal) - 1)
        if signal[index] > signal[index - 1] and signal[index] > signal[index + 1]
    ]
    properties = {}
    if prominence is not None:
        properties["prominences"] = [signal[index] for index in indexes]
    if width is not None:
        properties.update(
            {
                "widths": [1.0 for _ in indexes],
                "left_ips": [index - 0.5 for index in indexes],
                "right_ips": [index + 0.5 for index in indexes],
            }
        )
    return indexes, properties


class DetectionScopeTest(unittest.TestCase):
    def setUp(self):
        self.detector = PeakDetectionTool()
        self.detector._scipy_functions = lambda: fake_find_peaks
        self.detector._measure_properties = lambda signal, indexes: fake_find_peaks(
            signal, prominence=(None, None), width=(None, None)
        )[1]

    def test_single_range_and_global_sample_index(self):
        result = detect_in_ranges(
            self.detector,
            list(range(7)),
            [0, 0, 0, 0, 8, 0, 0],
            [(3, 6)],
            detect_valleys=False,
        )
        self.assertEqual([record["sample_index"] for record in result["peak"]], [4])

    def test_multiple_disjoint_ranges(self):
        result = detect_in_ranges(
            self.detector,
            list(range(8)),
            [0, 5, 0, 0, 7, 0, 0, 0],
            [(0, 2), (3, 6)],
            detect_valleys=False,
        )
        self.assertEqual([record["sample_index"] for record in result["peak"]], [1, 4])

    def test_overlapping_ranges_are_merged(self):
        self.assertEqual(merge_ranges([(5, 10), (0, 6), (20, 25)]), [(0, 10), (20, 25)])
        self.assertEqual(parse_ranges("5-10; 0-6; 20:25"), [(0, 10), (20, 25)])
        self.assertEqual(format_ranges([(5, 10), (0, 6)]), "0-10")

    def test_normalized_plotting_converts_without_changing_storage(self):
        raw_ranges = [(10.0, 20.0), (30.0, 40.0)]
        self.assertEqual(ranges_for_plot(raw_ranges, lambda value: value * 1.5), [(15, 30), (45, 60)])
        self.assertEqual(raw_ranges, [(10.0, 20.0), (30.0, 40.0)])

    def test_current_map_extent_reuses_raw_visibility_ranges(self):
        processing = DataProcessingTool(1)
        processing.pixel_size = 2
        profile = processing.getProfileLines([[-5, 5], [15, 5]])
        self.assertEqual(
            profile_visible_ranges(profile, QgsRectangle(0, 0, 10, 10)),
            [(10.0, 30.0)],
        )

    def test_nan_gaps_remain_independent_runs(self):
        result = detect_in_ranges(
            self.detector,
            list(range(7)),
            [0, 5, 0, None, 0, 6, 0],
            [(0, 6)],
            detect_valleys=False,
        )
        self.assertEqual([record["sample_index"] for record in result["peak"]], [1, 5])

    def test_map_extent_detection_accumulates_and_empty_extent_is_no_op(self):
        processing = DataProcessingTool(1)
        processing.pixel_size = 2
        profile = processing.getProfileLines([[0, 5], [20, 5]])
        x_values = [2.0 * i for i in range(21)]
        y_values = [5 if i in (3, 16) else 0 for i in range(21)]
        store = FeaturePointStore()
        snapshots = []
        for extent in (QgsRectangle(0, 0, 8, 10), QgsRectangle(12, 0, 20, 10),
                       QgsRectangle(30, 0, 40, 10)):
            ranges = profile_visible_ranges(profile, extent)
            detected = detect_in_ranges(self.detector, x_values, y_values, ranges, detect_valleys=False)
            records = [{**item, "distance": x_values[item["sample_index"]]} for item in detected["peak"]]
            snapshots.append(store.replace_auto_in_ranges(0, "raster", records, ranges))
        self.assertEqual([p["sample_index"] for p in snapshots[0]], [3])
        self.assertEqual([p["sample_index"] for p in snapshots[1]], [3, 16])
        self.assertEqual(snapshots[1][0], snapshots[0][0])
        self.assertEqual(snapshots[2], snapshots[1])

    def test_min_distance_is_not_applied_across_separate_ranges(self):
        result = detect_in_ranges(
            self.detector,
            list(range(7)),
            [0, 5, 0, 0, 6, 0, 0],
            [(0, 2), (3, 6)],
            detect_valleys=False,
            min_distance=100,
        )
        self.assertEqual([record["sample_index"] for record in result["peak"]], [1, 4])

    def test_excluded_samples_do_not_reach_detector(self):
        calls = []

        class RecordingDetector:
            def detect(self, x_values, y_values, **options):
                calls.append((list(x_values), list(y_values)))
                return {"peak": [], "valley": []}

        detect_in_ranges(
            RecordingDetector(),
            list(range(9)),
            list(range(9)),
            [(2, 4), (7, 8)],
        )
        self.assertEqual(calls, [([2, 3, 4], [2, 3, 4]), ([7, 8], [7, 8])])


if __name__ == "__main__":
    unittest.main()
