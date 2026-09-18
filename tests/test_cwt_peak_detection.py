"""Real-SciPy regressions for physical-scale CWT and shared post-processing."""

import math
import unittest

from tools.detectionScope import detect_in_ranges
from tools.featurePointStore import FeaturePointStore
from tools.peakDetectionTool import PeakDetectionTool

try:
    import numpy as np
    from scipy.signal import find_peaks
except ImportError:
    np = None


@unittest.skipIf(np is None, "SciPy/NumPy are not installed in this Python environment")
class CwtPeakDetectionTest(unittest.TestCase):
    def setUp(self):
        self.tool = PeakDetectionTool()

    @staticmethod
    def profile(features, spacing=0.5):
        x = np.arange(0, 240 + spacing / 2, spacing)
        y = sum(height * np.exp(-0.5 * ((x - center) / sigma) ** 2)
                for center, sigma, height in features)
        return x.tolist(), y.tolist()

    def detect(self, x, y, **options):
        defaults = dict(algorithm="cwt", detect_valleys=False, prominence=0.2,
                        cwt_min_scale=0.5, cwt_max_scale=12, cwt_num_scales=32)
        defaults.update(options)
        return self.tool.detect(x, y, **defaults)

    def assert_centers(self, records, centers, tolerance=0.5):
        self.assertEqual(len(records), len(centers), records)
        for record, center in zip(records, centers):
            self.assertAlmostEqual(record["distance"], center, delta=tolerance)

    def test_narrow_peak(self):
        x, y = self.profile([(60, 1, 5)])
        self.assert_centers(self.detect(x, y)["peak"], [60])

    def test_broad_peak_and_physical_width(self):
        x, y = self.profile([(120, 9, 5)])
        records = self.detect(x, y)["peak"]
        self.assert_centers(records, [120])
        self.assertAlmostEqual(records[0]["width"], 2 * math.sqrt(2 * math.log(2)) * 9, delta=0.05)

    def test_close_peaks(self):
        x, y = self.profile([(60, 1, 5), (66, 1, 4)])
        self.assert_centers(self.detect(x, y, cwt_max_scale=3)["peak"], [60, 66])

    def test_mixed_widths(self):
        x, y = self.profile([(45, 1, 5), (120, 8, 6), (190, 3, 4)])
        self.assert_centers(self.detect(x, y)["peak"], [45, 120, 190])

    def test_noise_and_changing_baseline(self):
        x, y = self.profile([(50, 2, 5), (160, 6, 8)])
        y = (np.array(y) + np.array(x) * 0.004
             + np.random.default_rng(1234).normal(0, 0.035, len(y))).tolist()
        self.assert_centers(self.detect(x, y, prominence=1)["peak"], [50, 160], tolerance=1.5)

    def test_valleys_use_inverted_signal_and_original_values(self):
        x, y = self.profile([(60, 2, -5), (160, 6, -8)])
        result = self.detect(x, y, detect_peaks=False, detect_valleys=True)
        self.assert_centers(result["valley"], [60, 160])
        self.assertEqual(result["peak"], [])
        for record in result["valley"]:
            self.assertEqual(record["value"], y[record["sample_index"]])
            self.assertEqual(record["algorithm"], "cwt")

    def test_nan_gaps_prevent_distance_and_prominence_coupling(self):
        x, y = self.profile([(60, 2, 5), (180, 4, 100)])
        y = [float("nan") if 100 <= value <= 120 else signal for value, signal in zip(x, y)]
        result = self.detect(x, y, min_distance=1000,
                             prominence_mode="local_range_percent", prominence=50,
                             prominence_window=1000)
        self.assert_centers(result["peak"], [60, 180])

    def test_detection_scope_isolates_cwt_and_all_filters(self):
        x, y = self.profile([(40, 2, 5), (90, 1, 10000), (160, 4, 8)])
        options = dict(algorithm="cwt", detect_valleys=False, min_distance=1000,
                       cwt_min_scale=0.5, cwt_max_scale=8,
                       prominence_mode="local_range_percent", prominence=50,
                       prominence_window=1000)
        result = detect_in_ranges(self.tool, x, y, [(20, 65), (130, 190)], **options)
        self.assert_centers(result["peak"], [40, 160])
        for record in result["peak"]:
            self.assertEqual(x[record["sample_index"]], record["distance"])
        # Changing excluded samples cannot influence CWT or property calculation.
        changed = [1e9 if 65 < value < 130 else signal for value, signal in zip(x, y)]
        self.assertEqual(result, detect_in_ranges(self.tool, x, changed, [(20, 65), (130, 190)], **options))

    def test_physical_scales_at_different_and_irregular_sample_spacing(self):
        for spacing in (0.25, 1, 2):
            x, y = self.profile([(60, 3, 5), (160, 8, 6)], spacing)
            self.assert_centers(self.detect(x, y)["peak"], [60, 160], tolerance=spacing)
        calls = []
        self.tool._cwt_function = lambda: lambda signal, widths, **options: calls.append((widths, options)) or []
        for x in ([0, 0.25, 0.5, 0.75, 1], [0, 2, 4, 6, 8], [0, 1, 2.1, 3.1, 4.1]):
            self.detect(x, [0, 1, 4, 1, 0], cwt_min_scale=1, cwt_max_scale=3, cwt_num_scales=3, cwt_min_snr=2)
        for (widths, options), expected in zip(calls, ([4, 8, 12], [0.5, 1, 1.5], [1, 2, 3])):
            np.testing.assert_allclose(widths, expected)
            self.assertEqual(options, {"min_snr": 2})

    def test_common_adaptive_modes_for_both_finders(self):
        x, y = self.profile([(60, 2, 5), (160, 6, 8)])
        for mode, threshold in (("absolute", 1), ("local_range_percent", 50),
                                ("local_sd", 1), ("local_mad", 1)):
            cwt = self.detect(x, y, prominence_mode=mode, prominence=threshold, prominence_window=20)
            standard = self.detect(x, y, algorithm="standard", prominence_mode=mode,
                                   prominence=threshold, prominence_window=20)
            self.assert_centers(cwt["peak"], [60, 160])
            self.assertEqual([{k: v for k, v in record.items() if k != "algorithm"} for record in cwt["peak"]],
                             [{k: v for k, v in record.items() if k != "algorithm"} for record in standard["peak"]])
        self.assertEqual(self.detect(x, y, prominence_mode="local_range_percent", prominence=101,
                                     prominence_window=1000)["peak"], [])

    def test_common_min_width_in_um(self):
        for spacing in (0.25, 2):
            x, y = self.profile([(60, 2, 5), (160, 8, 6)], spacing)
            for algorithm in ("standard", "cwt"):
                self.assert_centers(self.detect(x, y, algorithm=algorithm, min_width=10)["peak"], [160])

    def test_common_min_distance_in_um(self):
        x, y = self.profile([(60, 1, 5), (66, 1, 8)])
        for algorithm in ("standard", "cwt"):
            self.assert_centers(self.detect(x, y, algorithm=algorithm, cwt_max_scale=3, min_distance=6)["peak"], [60, 66])
            self.assert_centers(self.detect(x, y, algorithm=algorithm, cwt_max_scale=3, min_distance=6.01)["peak"], [66])

    def test_refinement_deduplicates_plateaus_and_rejects_distant_centers(self):
        self.tool._cwt_function = lambda: lambda *args, **kwargs: [0, 2, 3, 4, 6, 12]
        x = list(range(14))
        y = [0, 0, 1, 5, 5, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        result = self.detect(x, y, cwt_min_scale=1)["peak"]
        self.assertEqual([record["sample_index"] for record in result], [3])

    def test_refinement_ties_choose_height_then_lower_index(self):
        self.tool._cwt_function = lambda: lambda *args, **kwargs: [2]
        self.assert_centers(self.detect([0, 1, 2, 3, 4], [0, 5, 0, 8, 0])["peak"], [3])
        self.assert_centers(self.detect([0, 1, 2, 3, 4], [0, 5, 0, 5, 0])["peak"], [1])

    def test_short_flat_and_invalid_runs(self):
        for x, y in (([], []), ([0], [5]), ([0, 1], [0, 5]),
                     ([0, 0, 0], [0, 5, 0]), (list(range(10)), [1] * 10)):
            self.assertEqual(self.detect(x, y)["peak"], [])
        for settings in ({"cwt_min_scale": 0}, {"cwt_max_scale": 0.1},
                         {"cwt_min_snr": -1}, {"cwt_min_snr": float("nan")},
                         {"cwt_num_scales": 1}, {"cwt_num_scales": 2.5}, {"algorithm": "other"}):
            with self.assertRaises(ValueError):
                self.detect([0, 1, 2], [0, 5, 0], **settings)

    def test_manual_and_imported_points_survive_algorithm_switch(self):
        store = FeaturePointStore()
        for source, index in (("manual", 1), ("imported", 3)):
            record = dict(profile_index=0, raster_layer_id="layer", kind="peak", sample_index=index, distance=index)
            getattr(store, "add_" + source)(record)
        for algorithm in ("standard", "cwt", "standard"):
            result = self.detect(list(range(7)), [0, 5, 0, 8, 0, 6, 0], algorithm=algorithm)
            store.replace_auto(0, "layer", result["peak"])
            self.assertEqual([(r["sample_index"], r["source"]) for r in store.records_for(0, "layer")
                              if r["source"] != "auto"], [(1, "manual"), (3, "imported")])

    def test_standard_matches_original_scipy_properties(self):
        y = np.random.default_rng(77).normal(size=300)
        x = np.arange(len(y)) * 0.25
        for sign, kind in ((1, "peak"), (-1, "valley")):
            indexes, properties = find_peaks(sign * y, prominence=(None, None), width=(None, None))
            expected = [(int(index), properties["prominences"][i], properties["widths"][i] * 0.25)
                        for i, index in enumerate(indexes)
                        if properties["prominences"][i] >= 0.8 and properties["widths"][i] * 0.25 >= 0.4]
            records = self.tool.detect(x.tolist(), y.tolist(), prominence=0.8, min_width=0.4)[kind]
            self.assertEqual([r["sample_index"] for r in records], [r[0] for r in expected])
            np.testing.assert_allclose([r["prominence"] for r in records], [r[1] for r in expected])
            np.testing.assert_allclose([r["width"] for r in records], [r[2] for r in expected])


if __name__ == "__main__":
    unittest.main()
