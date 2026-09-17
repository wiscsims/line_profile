import math
import unittest

from tools.peakDetectionTool import PeakDetectionTool
from tools.profileProcessing import (
    SMOOTHING_GAUSSIAN,
    SMOOTHING_MOVING_AVERAGE,
    SMOOTHING_NONE,
    process_profile,
    smoothing_mode,
    smoothing_signature,
)


class ProfileProcessingTest(unittest.TestCase):
    def test_none_preserves_raw_values_and_length(self):
        raw = ([0, 1, 2], [1, None, 3])
        x_values, y_values = process_profile(raw, {"smoothingMode": SMOOTHING_NONE})
        self.assertEqual(x_values, raw[0])
        self.assertEqual(y_values[0], 1)
        self.assertTrue(math.isnan(y_values[1]))
        self.assertEqual(y_values[2], 3)
        self.assertEqual(raw, ([0, 1, 2], [1, None, 3]))

    def test_moving_average_is_same_length_and_marks_edges_missing(self):
        x_values, y_values = process_profile(
            ([0, 1, 2, 3, 4], [0, 3, 6, 3, 0]),
            {"smoothingMode": SMOOTHING_MOVING_AVERAGE, "movingAverageN": 3},
        )
        self.assertEqual(x_values, [0, 1, 2, 3, 4])
        self.assertTrue(math.isnan(y_values[0]))
        self.assertEqual(y_values[1:4], [3.0, 4.0, 3.0])
        self.assertTrue(math.isnan(y_values[4]))

    def test_moving_average_does_not_smooth_across_missing_gap(self):
        _, y_values = process_profile(
            ([0, 1, 2, 3, 4, 5, 6], [0, 4, 0, None, 0, 6, 0]),
            {"smoothingMode": SMOOTHING_MOVING_AVERAGE, "movingAverageN": 3},
        )
        self.assertEqual(y_values[1], 4.0 / 3.0)
        self.assertTrue(math.isnan(y_values[3]))
        self.assertEqual(y_values[5], 2.0)

    def test_gaussian_sigma_zero_is_a_no_op_without_scipy(self):
        raw = ([0, 1, 2], [2, 5, 2])
        self.assertEqual(
            process_profile(raw, {"smoothingMode": SMOOTHING_GAUSSIAN, "gaussianSigmaUm": 0}),
            raw,
        )

    def test_gaussian_uses_per_run_median_physical_spacing(self):
        calls = []

        def filter_values(values, sigma):
            calls.append((list(values), sigma))
            return [value + sigma for value in values]

        x_values, y_values = process_profile(
            ([0, 1, 3, 4, 10, 12, 14], [1, 2, 3, 4, None, 5, 6]),
            {"smoothingMode": SMOOTHING_GAUSSIAN, "gaussianSigmaUm": 2},
            gaussian_filter=filter_values,
        )
        self.assertEqual(x_values, [0, 1, 3, 4, 10, 12, 14])
        self.assertEqual(calls, [([1.0, 2.0, 3.0, 4.0], 2.0), ([5.0, 6.0], 1.0)])
        self.assertEqual(y_values[:4], [3.0, 4.0, 5.0, 6.0])
        self.assertTrue(math.isnan(y_values[4]))
        self.assertEqual(y_values[5:], [6.0, 7.0])

    def test_gaussian_requires_positive_spacing(self):
        with self.assertRaisesRegex(ValueError, "positive profile spacing"):
            process_profile(
                ([1, 1], [2, 3]),
                {"smoothingMode": SMOOTHING_GAUSSIAN, "gaussianSigmaUm": 1},
                gaussian_filter=lambda values, sigma: values,
            )

    def test_legacy_moving_average_configuration_remains_supported(self):
        self.assertEqual(smoothing_mode({"movingAverage": 2}), SMOOTHING_MOVING_AVERAGE)
        self.assertEqual(smoothing_mode({"movingAverage": 0}), SMOOTHING_NONE)

    def test_smoothing_signature_changes_with_any_processing_setting(self):
        base = {"smoothingMode": SMOOTHING_MOVING_AVERAGE, "movingAverageN": 5, "gaussianSigmaUm": 0}
        self.assertNotEqual(smoothing_signature(base), smoothing_signature({**base, "movingAverageN": 7}))
        self.assertNotEqual(smoothing_signature(base), smoothing_signature({**base, "smoothingMode": SMOOTHING_GAUSSIAN}))

    def test_peak_detection_receives_the_processed_values(self):
        _, processed_y = process_profile(
            ([0, 1, 2, 3, 4], [0, 6, 0, 3, 0]),
            {"smoothingMode": SMOOTHING_MOVING_AVERAGE, "movingAverageN": 3},
        )
        tool = PeakDetectionTool()
        captured = []

        def find_peaks(signal, **options):
            captured.append(list(signal))
            return [], {}

        tool._scipy_functions = lambda: find_peaks
        tool.detect([0, 1, 2, 3, 4], processed_y, detect_valleys=False)
        self.assertEqual(captured, [[2.0, 3.0, 1.0]])


if __name__ == "__main__":
    unittest.main()
