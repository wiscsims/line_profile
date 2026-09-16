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
    if prominence is not None:
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
    return candidates, properties


def fake_gaussian_filter(signal, sigma):
    padded = [0] + list(signal) + [0]
    return [
        0.25 * padded[index] + 0.5 * padded[index + 1] + 0.25 * padded[index + 2]
        for index in range(len(signal))
    ]


class PeakDetectionToolTest(unittest.TestCase):
    def setUp(self):
        self.tool = PeakDetectionTool()
        self.tool._scipy_functions = lambda: (fake_find_peaks, fake_gaussian_filter)

    def test_detects_peaks_and_valleys(self):
        y = [0, 1, 5, 1, 0, 2, 8, 2, 0]
        result = self.tool.detect(list(range(len(y))), y)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [2, 6])
        self.assertEqual([item["sample_index"] for item in result["valley"]], [4])

    def test_prominence_filters_small_peak(self):
        y = [0, 2, 0, 0, 6, 0]
        result = self.tool.detect(range(len(y)), y, detect_valleys=False, prominence=3)
        self.assertEqual([item["sample_index"] for item in result["peak"]], [4])

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

    def test_min_distance_is_not_forwarded_to_scipy_sample_distance(self):
        calls = []

        def recording_find_peaks(signal, **options):
            calls.append(options)
            return [], {}

        self.tool._scipy_functions = lambda: (recording_find_peaks, fake_gaussian_filter)
        self.tool.detect([0, 1, 2], [0, 5, 0], detect_valleys=False, min_distance=2.5)
        self.assertEqual(calls, [{}])

    def test_smoothing_reports_raw_value(self):
        y = [0, 0, 10, 0, 0]
        result = self.tool.detect(range(len(y)), y, detect_valleys=False, smoothing_sigma=1)
        self.assertEqual(result["peak"][0]["sample_index"], 2)
        self.assertEqual(result["peak"][0]["value"], 10)

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
