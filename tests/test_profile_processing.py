import math
import unittest

from tools.peakDetectionTool import PeakDetectionTool
from tools.profileProcessing import (
    SMOOTHING_GAUSSIAN,
    SMOOTHING_MOVING_AVERAGE,
    SMOOTHING_NONE,
    SMOOTHING_SAVGOL,
    process_profile,
    processed_data,
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
        self.assertNotEqual(smoothing_signature(base), smoothing_signature({**base, "smoothingMode": SMOOTHING_SAVGOL}))
        self.assertNotEqual(smoothing_signature(base), smoothing_signature({**base, "savgolWindowUm": 7}))
        self.assertNotEqual(smoothing_signature(base), smoothing_signature({**base, "savgolPolyOrder": 3}))

    def test_savgol_same_length_preserves_x_and_raw_data(self):
        raw = ([0, 1, 2, 3, 4], [0, 2, 5, 2, 0])
        x_values, y_values = process_profile(
            raw,
            {"smoothingMode": SMOOTHING_SAVGOL, "savgolWindowUm": 5, "savgolPolyOrder": 2},
            savgol_filter=lambda values, window, order, mode: [value + 1 for value in values],
        )
        self.assertEqual(x_values, raw[0])
        self.assertEqual(y_values, [1, 3, 6, 3, 1])
        self.assertEqual(raw, ([0, 1, 2, 3, 4], [0, 2, 5, 2, 0]))

    def test_savgol_known_quadratic_is_preserved_when_scipy_available(self):
        try:
            from scipy.signal import savgol_filter  # noqa: F401
        except ImportError:
            self.skipTest("SciPy is not installed in this Python environment")
        x_values = list(range(9))
        values = [index * index - 3 * index + 2 for index in x_values]
        _, smoothed = process_profile(
            (x_values, values),
            {"smoothingMode": SMOOTHING_SAVGOL, "savgolWindowUm": 5, "savgolPolyOrder": 2},
        )
        for expected, actual in zip(values, smoothed):
            self.assertAlmostEqual(actual, expected, places=10)

    def test_savgol_noise_reduction_uses_shared_processed_result(self):
        raw = ([0, 1, 2, 3, 4], [0, 4, 0, 4, 0])

        def reduce_noise(values, window, order, mode):
            self.assertEqual((window, order, mode), (5, 2, "interp"))
            return [1.0, 2.0, 2.0, 2.0, 1.0]

        _, smoothed = process_profile(
            raw,
            {"smoothingMode": SMOOTHING_SAVGOL, "savgolWindowUm": 5, "savgolPolyOrder": 2},
            savgol_filter=reduce_noise,
        )
        self.assertNotEqual(smoothed, raw[1])
        self.assertEqual(smoothed, [1.0, 2.0, 2.0, 2.0, 1.0])

    def test_savgol_uses_physical_window_for_different_and_irregular_spacing(self):
        calls = []

        def record(values, window, order, mode):
            calls.append((list(values), window, order, mode))
            return values

        config = {"smoothingMode": SMOOTHING_SAVGOL, "savgolWindowUm": 5, "savgolPolyOrder": 2}
        process_profile((list(range(7)), list(range(7))), config, savgol_filter=record)
        process_profile(([0, 2, 4, 6, 8], list(range(5))), config, savgol_filter=record)
        process_profile(([0, 1, 3, 4, 5], list(range(5))), config, savgol_filter=record)
        self.assertEqual([call[1] for call in calls], [5, 3, 5])
        self.assertTrue(all(call[3] == "interp" for call in calls))

    def test_savgol_does_not_cross_nan_gaps(self):
        calls = []

        def record(values, window, order, mode):
            calls.append(list(values))
            return [value + 0.5 for value in values]

        _, values = process_profile(
            ([0, 1, 2, 3, 4, 5, 6], [0, 1, 4, None, 0, 1, 4]),
            {"smoothingMode": SMOOTHING_SAVGOL, "savgolWindowUm": 5, "savgolPolyOrder": 2},
            savgol_filter=record,
        )
        self.assertEqual(calls, [[0.0, 1.0, 4.0], [0.0, 1.0, 4.0]])
        self.assertEqual(values[:3], [0.5, 1.5, 4.5])
        self.assertTrue(math.isnan(values[3]))
        self.assertEqual(values[4:], [0.5, 1.5, 4.5])

    def test_savgol_short_runs_and_invalid_configurations_remain_unsmoothed(self):
        raw = ([0, 1, 2], [2, 5, 2])
        reject = lambda *args, **kwargs: self.fail("invalid Savitzky–Golay run was filtered")
        self.assertEqual(
            process_profile(
                raw,
                {"smoothingMode": SMOOTHING_SAVGOL, "savgolWindowUm": 5, "savgolPolyOrder": 3},
                savgol_filter=reject,
            ),
            raw,
        )
        self.assertEqual(
            process_profile(
                raw,
                {"smoothingMode": SMOOTHING_SAVGOL, "savgolWindowUm": 0, "savgolPolyOrder": 2},
                savgol_filter=reject,
            ),
            raw,
        )
        self.assertEqual(
            process_profile(
                raw,
                {"smoothingMode": SMOOTHING_SAVGOL, "savgolWindowUm": 5, "savgolPolyOrder": -1},
                savgol_filter=reject,
            ),
            raw,
        )

    def test_savgol_plot_export_and_peak_use_one_processed_profile(self):
        raw = ([0, 1, 2, 3, 4], [0, 4, 0, 2, 0])
        _, smooth = process_profile(
            raw,
            {"smoothingMode": SMOOTHING_SAVGOL, "savgolWindowUm": 5, "savgolPolyOrder": 2},
            savgol_filter=lambda values, window, order, mode: [0.0, 1.0, 3.0, 1.0, 0.0],
        )
        descriptor = {"data": raw, "processed_data": (raw[0], smooth)}
        plot_values = processed_data(descriptor)
        export_values = processed_data(descriptor)
        tool = PeakDetectionTool()
        captured = []

        def find_peaks(signal, **options):
            captured.append(list(signal))
            return [], {}

        tool._scipy_functions = lambda: find_peaks
        tool.detect(*plot_values, detect_valleys=False)
        self.assertEqual(plot_values, export_values)
        self.assertEqual(captured, [smooth])

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
