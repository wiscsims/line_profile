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

    def test_imported_points_survive_auto_replacement_and_clear_auto(self):
        self.store.add_imported(record("peak", "ignored", 2))
        self.store.replace_auto(0, "raster", [record("valley", "auto", 4)])
        self.store.clear_auto(0, "raster")
        records = self.store.records_for(0, "raster")
        self.assertEqual([(item["sample_index"], item["source"]) for item in records], [(2, "imported")])

    def test_imported_duplicate_is_skipped_and_opposite_type_reclassifies(self):
        self.store.add_imported(record("peak", "ignored", 2))
        self.store.add_imported(record("peak", "ignored", 2))
        self.store.add_imported(record("valley", "ignored", 2))
        records = self.store.records_for(0, "raster")
        self.assertEqual([(item["kind"], item["source"]) for item in records], [("valley", "imported")])

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

    def test_scoped_auto_replace_preserves_auto_points_outside_scope(self):
        self.store.replace_auto(
            0,
            "raster",
            [record("peak", "auto", 2), record("peak", "auto", 8)],
        )
        self.store.replace_auto_in_ranges(
            0,
            "raster",
            [record("valley", "auto", 4)],
            [(0, 5)],
        )
        records = self.store.records_for(0, "raster")
        self.assertEqual(
            [(item["sample_index"], item["kind"]) for item in records],
            [(4, "valley"), (8, "peak")],
        )

    def test_empty_scoped_auto_replace_changes_nothing(self):
        self.store.replace_auto(
            0,
            "raster",
            [record("peak", "auto", 2), record("peak", "auto", 8)],
        )
        self.store.add_manual(record(sample_index=3))
        self.store.add_imported(record(sample_index=4))
        before = self.store.records_for(0, "raster")
        self.assertEqual(self.store.replace_auto_in_ranges(0, "raster", [], []), before)
        self.assertEqual(self.store.records_for(0, "raster"), before)
        self.store.replace_auto_in_ranges(1, "other", [record("peak", "auto", 2)], [])
        self.assertNotIn((1, "other"), self.store.keys())

    def test_scoped_auto_replace_preserves_manual_and_imported_points(self):
        manual = record("peak", "manual", 2)
        imported = record("valley", "imported", 3)
        self.store.records[(0, "raster")] = [manual, imported]
        self.store.replace_auto_in_ranges(
            0,
            "raster",
            [record("valley", "auto", 2), record("peak", "auto", 3), record("peak", "auto", 4)],
            [(0, 5)],
        )
        records = self.store.records_for(0, "raster")
        self.assertEqual(
            [(item["sample_index"], item["source"]) for item in records],
            [(2, "manual"), (3, "imported"), (4, "auto")],
        )

    def test_disjoint_scope_replaces_inside_only_and_deduplicates_results(self):
        before = self.store.replace_auto(
            0, "raster", [record("peak", "auto", i) for i in (1, 3, 5, 7, 9)]
        )
        result = self.store.replace_auto_in_ranges(
            0, "raster",
            [record("valley", "auto", i) for i in (1, 1, 5, 7)],
            [(1, 3), (7, 8)],
        )
        self.assertEqual([(p["sample_index"], p["kind"]) for p in result],
                         [(1, "valley"), (5, "peak"), (7, "valley"), (9, "peak")])
        self.assertEqual([p for p in result if p["sample_index"] in (5, 9)], [before[2], before[4]])

    def test_incremental_redetection_preserves_other_region_and_series(self):
        left = self.store.replace_auto_in_ranges(0, "raster", [record("peak", "auto", 2)], [(0, 4)])
        self.store.replace_auto(1, "raster", [record("peak", "auto", 3)])
        self.store.replace_auto(0, "other", [record("peak", "auto", 3)])
        others = {key: self.store.records_for(*key) for key in ((1, "raster"), (0, "other"))}
        self.store.replace_auto_in_ranges(0, "raster", [record("peak", "auto", 8)], [(6, 10)])
        self.assertEqual(len(self.store.records_for(0, "raster")), 2)
        # A stricter threshold finds nothing on the right; only that region is cleared.
        self.store.replace_auto_in_ranges(0, "raster", [], [(6, 10)])
        self.assertEqual(self.store.records_for(0, "raster"), left)
        self.assertEqual({key: self.store.records_for(*key) for key in others}, others)

    def test_full_replace_removes_all_old_auto_and_keeps_all_curated(self):
        self.store.replace_auto(0, "raster", [record("peak", "auto", i) for i in (1, 8)])
        manual = self.store.add_manual(record(sample_index=2))
        imported = self.store.add_imported(record(sample_index=3))
        result = self.store.replace_auto(0, "raster", [record("peak", "auto", i) for i in (2, 3, 5)])
        self.assertEqual(result[:2], [manual, imported])
        self.assertEqual([p["sample_index"] for p in result], [2, 3, 5])

    def test_import_promotes_matching_auto_and_recalculates_properties(self):
        self.store.replace_auto(0, "raster", [record("peak", "auto", 2)])
        imported = self.store.add_imported({**record(), "value": 42, "point": (2, 7)})
        self.assertEqual(imported["source"], "imported")
        self.assertEqual((imported["value"], imported["point"]), (42, (2, 7)))
        self.assertEqual(self.store.records_for(0, "raster"), [imported])
        self.store.clear_auto(0, "raster")
        self.store.replace_auto_in_ranges(0, "raster", [record("valley", "auto", 2)], [(0, 5)])
        self.store.replace_auto(0, "raster", [record("peak", "auto", 2)])
        self.assertEqual(self.store.records_for(0, "raster"), [imported])

    def test_matching_import_preserves_existing_manual_or_imported_record(self):
        for add in (self.store.add_manual, self.store.add_imported):
            with self.subTest(source=add.__name__):
                self.store.clear_all()
                original = add(record())
                self.assertEqual(self.store.add_imported({**record(), "value": 999}), original)
                self.assertEqual(self.store.records_for(0, "raster"), [original])

    def test_clear_in_scope_preserves_outside_and_curated_by_default(self):
        self.store.records[(0, "raster")] = [
            record("peak", "manual", 2),
            record("valley", "imported", 3),
            record("peak", "auto", 4),
            record("peak", "auto", 8),
        ]
        removed = self.store.clear_in_ranges(0, "raster", [(0, 5)])
        self.assertEqual([item["sample_index"] for item in removed], [4])
        self.store.clear_in_ranges(0, "raster", [(0, 5)], include_curated=True)
        self.assertEqual(
            [item["sample_index"] for item in self.store.records_for(0, "raster")],
            [8],
        )


if __name__ == "__main__":
    unittest.main()
