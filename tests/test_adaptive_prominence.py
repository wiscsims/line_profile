import math
import unittest

from tools.detectionScope import detect_in_ranges
from tools.peakDetectionTool import (
    PROMINENCE_LOCAL_MAD,
    PROMINENCE_LOCAL_RANGE,
    PROMINENCE_LOCAL_SD,
    PeakDetectionTool,
)


def fake_find_peaks(signal, prominence=None, width=None):
    values = [float(value) for value in signal]
    indexes = [
        index
        for index in range(1, len(values) - 1)
        if values[index] > values[index - 1] and values[index] > values[index + 1]
    ]
    prominences = [
        min(values[index] - min(values[: index + 1]), values[index] - min(values[index:]))
        for index in indexes
    ]
    return indexes, {
        "prominences": prominences,
        "widths": [1.0 for _ in indexes],
        "left_ips": [index - 0.5 for index in indexes],
        "right_ips": [index + 0.5 for index in indexes],
    }


def candidate(index, prominence):
    return {
        "sample_index": index,
        "prominence": prominence,
        "width": 1.0,
        "_run_index": index,
        "_profile_distance": float(index),
        "_prominence": prominence,
        "_detection_height": prominence,
    }


class AdaptiveProminenceTest(unittest.TestCase):
    def setUp(self):
        self.tool = PeakDetectionTool()
        self.tool._scipy_functions = lambda: fake_find_peaks
        self.tool._measure_properties = lambda signal, indexes: fake_find_peaks(signal)[1]

    def filtered(self, y_values, candidates, mode, value, window):
        return self.tool.filter_candidates(
            candidates,
            [float(index) for index in range(len(y_values))],
            y_values,
            prominence_mode=mode,
            prominence=value,
            prominence_window=window,
        )

    def test_constant_noise_has_zero_local_sd_and_mad_thresholds(self):
        values = [5.0, 5.0, 5.0]
        self.assertEqual(len(self.filtered(values, [candidate(1, 0.1)], PROMINENCE_LOCAL_SD, 3, 2)), 1)
        self.assertEqual(len(self.filtered(values, [candidate(1, 0.1)], PROMINENCE_LOCAL_MAD, 3, 2)), 1)

    def test_changing_noise_uses_candidate_local_sd(self):
        values = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -4.0, 4.0, -4.0]
        retained = self.filtered(
            values,
            [candidate(1, 1.0), candidate(7, 1.0)],
            PROMINENCE_LOCAL_SD,
            2.0,
            2.0,
        )
        self.assertEqual([item["sample_index"] for item in retained], [1])

    def test_changing_amplitude_uses_local_range_percentage(self):
        values = [0.0, 2.0, 0.0, 0.0, 0.0, 10.0, 0.0]
        retained = self.filtered(
            values,
            [candidate(1, 1.5), candidate(5, 4.0)],
            PROMINENCE_LOCAL_RANGE,
            50.0,
            2.0,
        )
        self.assertEqual([item["sample_index"] for item in retained], [1])

    def test_sd_and_mad_formulas(self):
        sd = self.tool._prominence_threshold(
            candidate(1, 1), [0, 1, 2], [0, 1, 2], PROMINENCE_LOCAL_SD, 2, 2
        )
        mad = self.tool._prominence_threshold(
            candidate(1, 1), [0, 1, 2], [0, 1, 2], PROMINENCE_LOCAL_MAD, 2, 2
        )
        self.assertAlmostEqual(sd, 2 * math.sqrt(2.0 / 3.0))
        self.assertAlmostEqual(mad, 2 * 1.4826)

    def test_changing_baseline_does_not_change_local_mad(self):
        low = self.tool._prominence_threshold(
            candidate(2, 1), [0, 1, 2, 3, 4], [0, 1, 2, 1, 0], PROMINENCE_LOCAL_MAD, 2, 4
        )
        high = self.tool._prominence_threshold(
            candidate(2, 1), [0, 1, 2, 3, 4], [100, 101, 102, 101, 100], PROMINENCE_LOCAL_MAD, 2, 4
        )
        self.assertEqual(low, high)

    def test_window_uses_raw_distance_and_available_finite_edge(self):
        threshold = self.tool._prominence_threshold(
            candidate(0, 1),
            [0.0, 0.25, 10.0],
            [2.0, 4.0, 100.0],
            PROMINENCE_LOCAL_RANGE,
            50.0,
            1.0,
        )
        self.assertEqual(threshold, 1.0)

    def test_mad_is_robust_to_strong_outlier(self):
        values = [0.0, 0.0, 1.0, 0.0, 50.0]
        mad = self.filtered(values, [candidate(2, 1.0)], PROMINENCE_LOCAL_MAD, 1.0, 4.0)
        sd = self.filtered(values, [candidate(2, 1.0)], PROMINENCE_LOCAL_SD, 1.0, 4.0)
        self.assertEqual(len(mad), 1)
        self.assertEqual(sd, [])

    def test_nan_gap_bounds_the_adaptive_window(self):
        result = self.tool.detect(
            range(7),
            [0, 3, 0, None, 0, 100, 0],
            detect_valleys=False,
            prominence_mode=PROMINENCE_LOCAL_RANGE,
            prominence=50,
            prominence_window=100,
        )
        self.assertEqual([item["sample_index"] for item in result["peak"]], [1, 5])

    def test_selected_ranges_are_independent_adaptive_windows(self):
        result = detect_in_ranges(
            self.tool,
            list(range(9)),
            [0, 3, 0, 0, 100, 0, 0, 4, 0],
            [(0, 2), (6, 8)],
            detect_valleys=False,
            prominence_mode=PROMINENCE_LOCAL_RANGE,
            prominence=50,
            prominence_window=100,
        )
        self.assertEqual([item["sample_index"] for item in result["peak"]], [1, 7])

    def test_peaks_and_valleys_use_the_same_adaptive_filter(self):
        result = self.tool.detect(
            range(5),
            [0, 4, 0, -5, 0],
            prominence_mode=PROMINENCE_LOCAL_RANGE,
            prominence=50,
            prominence_window=2,
        )
        self.assertEqual([item["sample_index"] for item in result["peak"]], [1])
        self.assertEqual([item["sample_index"] for item in result["valley"]], [3])


if __name__ == "__main__":
    unittest.main()
