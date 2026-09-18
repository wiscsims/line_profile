import unittest

from tools.peakDetectionTool import PeakDetectionTool


def fake_find_peaks(signal, prominence=None, distance=None, width=None):
    signal = [float(value) for value in signal]
    candidates = [
        index
        for index in range(1, len(signal) - 1)
        if signal[index] > signal[index - 1] and signal[index] > signal[index + 1]
    ]
    prominences = [
        min(signal[index] - min(signal[: index + 1]), signal[index] - min(signal[index:]))
        for index in candidates
    ]
    if prominence is not None and not isinstance(prominence, tuple):
        filtered = [(index, value) for index, value in zip(candidates, prominences) if value >= prominence]
        candidates = [item[0] for item in filtered]
        prominences = [item[1] for item in filtered]
    if distance is not None:
        accepted = []
        for index in sorted(candidates, key=lambda item: signal[item], reverse=True):
            if all(abs(index - other) >= distance for other in accepted):
                accepted.append(index)
        candidates = sorted(accepted)
        prominences = [
            min(signal[index] - min(signal[: index + 1]), signal[index] - min(signal[index:]))
            for index in candidates
        ]
    properties = {"prominences": prominences} if prominence is not None else {}
    if width is not None:
        properties.update(
            {
                "widths": [1.0 for _ in candidates],
                "left_ips": [index - 0.5 for index in candidates],
                "right_ips": [index + 0.5 for index in candidates],
            }
        )
    return candidates, properties


class PeakDetectionToolTest(unittest.TestCase):
    def setUp(self):
        self.tool = PeakDetectionTool()
        self.tool._scipy_functions = lambda: fake_find_peaks

    def use_width_properties(self, index, left_ips, right_ips):
        def find_peaks(signal, **options):
            return [index], {
                "widths": [right_ips - left_ips],
                "left_ips": [left_ips],
                "right_ips": [right_ips],
            }

        self.tool._scipy_functions = lambda: find_peaks

    def test_detects_peaks_and_valleys(self):
        y = [0, 1, 5, 1, 0, 2, 8, 2, 0]
        result = self.tool.detect(list(range(len(y))), y)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [2, 6])
        self.assertEqual([item["sample_index"] for item in result["valley"]], [4])

    def test_prominence_filters_small_peak(self):
        y = [0, 2, 0, 0, 6, 0]
        result = self.tool.detect(range(len(y)), y, detect_valleys=False, prominence=3)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [4])

    def test_absolute_prominence_default_is_backward_compatible(self):
        y = [0, 2, 0, 0, 6, 0]
        default = self.tool.detect(range(len(y)), y, detect_valleys=False, prominence=3)
        explicit = self.tool.detect(
            range(len(y)), y, detect_valleys=False, prominence=3, prominence_mode="absolute"
        )
        self.assertEqual(default, explicit)

    def test_min_distance_uses_physical_distance_at_one_um_sampling(self):
        y = [0, 5, 0, 8, 0]
        result = self.tool.detect(range(len(y)), y, detect_valleys=False, min_distance=3)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [3])

    def test_min_distance_uses_physical_distance_at_quarter_um_sampling(self):
        x = [index * 0.25 for index in range(26)]
        y = [0] * len(x)
        y[4] = 5
        y[22] = 8
        result = self.tool.detect(x, y, detect_valleys=False, min_distance=5)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [22])
        self.assertEqual(result["peak"][0]["distance"], 5.5)

    def test_min_distance_uses_physical_distance_at_two_um_sampling(self):
        x = [0, 2, 4, 6, 8]
        y = [0, 5, 0, 8, 0]
        result = self.tool.detect(x, y, detect_valleys=False, min_distance=5)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [3])

    def test_min_distance_handles_slightly_irregular_x_spacing(self):
        x = [0.0, 1.0, 2.0, 3.1, 4.1, 5.1, 6.1]
        y = [0, 5, 0, 0, 8, 0, 0]
        result = self.tool.detect(x, y, detect_valleys=False, min_distance=3.2)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [4])

    def test_features_exactly_at_min_distance_are_retained(self):
        x = list(range(8))
        y = [0, 5, 0, 0, 0, 0, 8, 0]
        result = self.tool.detect(x, y, detect_valleys=False, min_distance=5)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [1, 6])

    def test_features_below_min_distance_keep_the_stronger_candidate(self):
        x = [0, 1, 2, 3, 4, 5.9, 6.9]
        y = [0, 5, 0, 0, 0, 8, 0]
        result = self.tool.detect(
            x, y, detect_valleys=False, prominence=0.1, min_distance=5
        )
        self.assertEqual([item["sample_index"] for item in result["peak"]], [5])

    def test_peaks_and_valleys_are_filtered_independently(self):
        x = list(range(5))
        y = [0, 5, 0, -8, 0]
        result = self.tool.detect(x, y, min_distance=5)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [1])
        self.assertEqual([item["sample_index"] for item in result["valley"]], [3])

    def test_zero_min_distance_is_unconstrained(self):
        y = [0, 5, 0, 0, 8, 0]
        result = self.tool.detect(range(len(y)), y, detect_valleys=False, min_distance=0)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [1, 4])

    def test_width_is_physical_at_one_um_and_quarter_um_sampling(self):
        self.use_width_properties(2, 1.0, 3.0)
        one_um = self.tool.detect(
            [0, 1, 2, 3, 4], [0, 0, 5, 0, 0], detect_valleys=False
        )["peak"][0]

        self.use_width_properties(4, 0.0, 8.0)
        quarter_um = self.tool.detect(
            [index * 0.25 for index in range(10)],
            [0, 0, 0, 0, 5, 0, 0, 0, 0, 0],
            detect_valleys=False,
        )["peak"][0]

        self.assertAlmostEqual(one_um["width"], 2.0)
        self.assertAlmostEqual(quarter_um["width"], 2.0)

    def test_min_width_uses_physical_distance_at_two_um_sampling(self):
        self.use_width_properties(2, 1.5, 2.5)
        x = [0, 2, 4, 6, 8]
        y = [0, 0, 5, 0, 0]
        retained = self.tool.detect(x, y, detect_valleys=False, min_width=2)
        rejected = self.tool.detect(x, y, detect_valleys=False, min_width=2.01)
        self.assertEqual([item["sample_index"] for item in retained["peak"]], [2])
        self.assertAlmostEqual(retained["peak"][0]["width"], 2.0)
        self.assertEqual(rejected["peak"], [])

    def test_width_uses_interpolation_for_irregular_x_spacing(self):
        self.use_width_properties(2, 1.5, 3.5)
        x = [0.0, 1.0, 2.1, 3.0, 4.2, 5.1]
        y = [0, 0, 5, 0, 0, 0]
        result = self.tool.detect(x, y, detect_valleys=False)
        self.assertAlmostEqual(result["peak"][0]["width"], 2.05)

    def test_features_exactly_at_min_width_are_retained(self):
        self.use_width_properties(2, 0.0, 5.0)
        result = self.tool.detect(
            [0, 1, 2, 3, 4, 5], [0, 0, 5, 0, 0, 0],
            detect_valleys=False, min_width=5,
        )
        self.assertEqual([item["sample_index"] for item in result["peak"]], [2])

    def test_zero_min_width_does_not_filter_and_width_is_still_physical(self):
        y = [0, 5, 0]
        result = self.tool.detect(range(len(y)), y, detect_valleys=False, min_width=0)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [1])
        self.assertAlmostEqual(result["peak"][0]["width"], 1.0)

    def test_width_does_not_cross_nan_separated_runs(self):
        y = [0, 5, 0, None, 0, 6, 0]
        result = self.tool.detect(
            range(len(y)), y, detect_valleys=False, min_width=1
        )
        self.assertEqual([item["sample_index"] for item in result["peak"]], [1, 5])
        self.assertEqual([item["width"] for item in result["peak"]], [1.0, 1.0])

    def test_valley_width_is_reported_in_physical_distance(self):
        y = [0, -5, 0]
        result = self.tool.detect(range(len(y)), y, detect_peaks=False, min_width=1)
        self.assertEqual([item["sample_index"] for item in result["valley"]], [1])
        self.assertAlmostEqual(result["valley"][0]["width"], 1.0)

    def test_min_distance_is_not_forwarded_to_scipy_sample_distance(self):
        calls = []

        def recording_find_peaks(signal, **options):
            calls.append(options)
            return [], {}

        self.tool._scipy_functions = lambda: recording_find_peaks
        self.tool.detect([0, 1, 2], [0, 5, 0], detect_valleys=False, min_distance=2.5)
        self.assertNotIn("distance", calls[0])

    def test_min_width_is_not_forwarded_to_scipy_sample_width(self):
        calls = []

        def recording_find_peaks(signal, **options):
            calls.append(options)
            return [], {}

        self.tool._scipy_functions = lambda: recording_find_peaks
        self.tool.detect([0, 1, 2], [0, 5, 0], detect_valleys=False, min_width=2.5)
        self.assertEqual(calls[0]["width"], (None, None))

    def test_manual_snap_and_edge_windows(self):
        y = [4, 1, 7, 2, 5]
        self.assertEqual(self.tool.snap_peak(y, 0, 2), 2)
        self.assertEqual(self.tool.snap_valley(y, 4, 2), 3)
        self.assertEqual(self.tool.snap_peak(y, 99, 1), 4)
        self.assertEqual(self.tool.snap_valley([None, None], 0, 2), None)

    def test_missing_values_split_detection_runs(self):
        y = [0, 5, 0, None, 0, 6, 0]
        result = self.tool.detect(range(len(y)), y, detect_valleys=False, min_distance=5)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [1, 5])

    def test_actual_scipy_find_peaks_when_available(self):
        if not PeakDetectionTool.scipy_available():
            self.skipTest("SciPy is not installed in this Python environment")
        tool = PeakDetectionTool()
        y = [0, 1, 5, 1, 0, 2, 8, 2, 0]
        result = tool.detect(range(len(y)), y, prominence=2)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [2, 6])
        self.assertEqual([item["sample_index"] for item in result["valley"]], [4])


if __name__ == "__main__":
    unittest.main()
