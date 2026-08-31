import unittest

from tools.featurePointStore import FeaturePointStore


def record(kind="peak", source="manual", sample_index=2):
    return {
        "kind": kind,
        "source": source,
        "profile_index": 0,
        "raster_layer_id": "raster",
        "sample_index": sample_index,
        "distance": float(sample_index),
        "value": 10,
        "point": (sample_index, 0),
        "prominence": None,
        "width": None,
    }


class FeaturePointStoreTest(unittest.TestCase):
    def setUp(self):
        self.store = FeaturePointStore()

    def test_duplicate_manual_point_is_not_added(self):
        self.store.add_manual(record())
        self.store.add_manual(record())
        self.assertEqual(len(self.store.records_for(0, "raster")), 1)

    def test_manual_reclassification_replaces_opposite_kind(self):
        self.store.add_manual(record("peak"))
        self.store.add_manual(record("valley"))
        records = self.store.records_for(0, "raster")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["kind"], "valley")
        self.assertEqual(records[0]["source"], "manual")

    def test_auto_rerun_preserves_manual_and_skips_same_sample(self):
        self.store.add_manual(record("peak", sample_index=2))
        self.store.replace_auto(0, "raster", [record("peak", "auto", 2), record("valley", "auto", 4)])
        self.store.replace_auto(0, "raster", [record("peak", "auto", 2), record("peak", "auto", 6)])
        records = self.store.records_for(0, "raster")
        self.assertEqual([(item["sample_index"], item["source"]) for item in records], [(2, "manual"), (6, "auto")])

    def test_clear_auto_preserves_manual(self):
        self.store.add_manual(record(sample_index=2))
        self.store.replace_auto(0, "raster", [record("valley", "auto", 4)])
        self.store.clear_auto(0, "raster")
        self.assertEqual([item["source"] for item in self.store.records_for(0, "raster")], ["manual"])

    def test_delete_nearest_respects_tolerance(self):
        self.store.add_manual(record(sample_index=5))
        self.assertIsNone(self.store.delete_nearest(0, "raster", 1, 2))
        self.assertIsNotNone(self.store.delete_nearest(0, "raster", 4, 2))
        self.assertEqual(self.store.records_for(0, "raster"), [])

    def test_profiles_are_independent(self):
        self.store.add_manual(record(sample_index=2))
        second = record(sample_index=3)
        second["profile_index"] = 1
        self.store.add_manual(second)
        self.store.clear_profile(0)
        self.assertEqual(self.store.records_for(0, "raster"), [])
        self.assertEqual(len(self.store.records_for(1, "raster")), 1)


if __name__ == "__main__":
    unittest.main()
