import os
import tempfile
import unittest

from tools.featurePointIO import (
    export_feature_points,
    map_imported_points,
    parse_import_rows,
    read_delimited_rows,
)
from tools.featurePointStore import FeaturePointStore
from tools.profileProcessing import process_profile


def point_record(kind="peak", source="imported", sample_index=1):
    return {
        "id": "point-{}-{}".format(kind, sample_index),
        "kind": kind,
        "source": source,
        "profile_index": 0,
        "raster_layer_id": "current-raster",
        "sample_index": sample_index,
        "distance": float(sample_index) * 5,
        "value": 10.0 + sample_index,
        "point": (100 + sample_index, 200 + sample_index),
        "prominence": 2.0,
        "width": 3.0,
        "data_label": "Raster — Band 1",
    }


class FeaturePointIOTest(unittest.TestCase):
    def write_file(self, name, contents):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, name)
        with open(path, "w", encoding="utf-8") as output:
            output.write(contents)
        return path

    def test_minimal_csv_and_malformed_rows(self):
        path = self.write_file(
            "points.csv",
            "distance_um,type\n1234.5,peak\nbad,valley\n1456.8,valley\n",
        )
        headers, rows = read_delimited_rows(path)
        entries, skipped = parse_import_rows(rows)
        self.assertIn("distance_um", headers)
        self.assertEqual([(entry["distance_um"], entry["kind"]) for entry in entries], [(1234.5, "peak"), (1456.8, "valley")])
        self.assertEqual(skipped, [3])

    def test_tsv_and_default_type(self):
        path = self.write_file("points.tsv", "distance_um\n2.5\n5.0\n")
        headers, rows = read_delimited_rows(path)
        entries, skipped = parse_import_rows(rows, default_type="valley")
        self.assertNotIn("type", headers)
        self.assertEqual([entry["kind"] for entry in entries], ["valley", "valley"])
        self.assertEqual(skipped, [])

    def test_tab_delimited_text_file(self):
        path = self.write_file("points.txt", "distance_um\ttype\n2.5\tpeak\n")
        headers, rows = read_delimited_rows(path)
        entries, skipped = parse_import_rows(rows)
        self.assertIn("type", headers)
        self.assertEqual([(entry["distance_um"], entry["kind"]) for entry in entries], [(2.5, "peak")])
        self.assertEqual(skipped, [])

    def test_export_round_trip(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "points.csv")
        export_feature_points(path, [point_record("peak"), point_record("valley", sample_index=2)])
        headers, rows = read_delimited_rows(path)
        entries, skipped = parse_import_rows(rows)
        self.assertTrue({"source", "profile", "data", "map_x", "map_y"}.issubset(headers))
        self.assertEqual([(entry["distance_um"], entry["kind"]) for entry in entries], [(5.0, "peak"), (10.0, "valley")])
        self.assertEqual(skipped, [])

    def test_distance_snapping_and_processed_value_recalculation(self):
        entries = [{"line_number": 2, "distance_um": 6.2, "kind": "peak"}]
        records, skipped = map_imported_points(
            entries,
            [0.0, 5.0, 10.0],
            [1.0, 99.0, 3.0],
            [(0, 0), (5, 7), (10, 0)],
            0,
            "current-raster",
            "Raster — Band 1",
        )
        self.assertEqual(skipped, [])
        self.assertEqual(records[0]["sample_index"], 1)
        self.assertEqual(records[0]["distance"], 5.0)
        self.assertEqual(records[0]["value"], 99.0)
        self.assertEqual(records[0]["point"], (5, 7))

    def test_out_of_range_distances_are_rejected_without_clamping(self):
        entries = [
            {"line_number": 2, "distance_um": -0.1, "kind": "peak"},
            {"line_number": 3, "distance_um": 10.1, "kind": "valley"},
        ]
        records, skipped = map_imported_points(
            entries, [0.0, 5.0, 10.0], [1, 2, 3], [(0, 0), (5, 0), (10, 0)], 0, "r", "data"
        )
        self.assertEqual(records, [])
        self.assertEqual(skipped, [2, 3])

    def test_normalization_does_not_affect_raw_distance_mapping(self):
        entries = [{"line_number": 2, "distance_um": 10.0, "kind": "peak"}]
        records, skipped = map_imported_points(
            entries, [0.0, 10.0, 20.0], [1, 7, 2], [(0, 0), (1, 1), (2, 2)], 1, "r", "data"
        )
        self.assertEqual(skipped, [])
        self.assertEqual((records[0]["profile_index"], records[0]["sample_index"], records[0]["distance"]), (1, 1, 10.0))

    def test_import_duplicate_and_reclassification_policy(self):
        store = FeaturePointStore()
        store.add_imported(point_record("peak"))
        store.add_imported(point_record("peak"))
        store.add_imported(point_record("valley"))
        records = store.records_for(0, "current-raster")
        self.assertEqual([(record["kind"], record["source"]) for record in records], [("valley", "imported")])

    def test_moving_average_edges_snap_inside_full_physical_extent(self):
        x_values, y_values = process_profile((list(range(15)), list(range(15))), {"movingAverage": True})
        entries = [{"line_number": i + 2, "distance_um": x, "kind": "peak"}
                   for i, x in enumerate((-0.1, 0, 14, 14.1))]
        records, skipped = map_imported_points(
            entries, x_values, y_values, [(x, 0) for x in x_values], 0, "r", "data"
        )
        self.assertEqual(skipped, [2, 5])
        self.assertEqual([(p["sample_index"], p["distance"], p["value"]) for p in records],
                         [(5, 5, 5), (9, 9, 9)])

    def test_internal_gap_snaps_to_nearest_finite_processed_sample(self):
        for missing in (float("nan"), float("inf"), -float("inf"), None):
            with self.subTest(missing=missing):
                records, skipped = map_imported_points(
                    [{"line_number": 2, "distance_um": 6, "kind": "valley"}],
                    [0, 5, 10], [1, missing, 7], [(0, 0), (5, 0), (10, 0)], 0, "r", "data"
                )
                self.assertEqual(skipped, [])
                self.assertEqual((records[0]["sample_index"], records[0]["value"]), (2, 7))

    def test_invalid_x_and_missing_or_invalid_centers_are_not_snap_candidates(self):
        records, skipped = map_imported_points(
            [{"line_number": 2, "distance_um": 8, "kind": "peak"}],
            [0, float("nan"), float("inf"), 5, 6, 7, 8, 9], [1] * 8,
            [(0, 0), (1, 1), (2, 2), None, (), (6, float("nan")), (float("inf"), 0)],
            0, "r", "data",
        )
        self.assertEqual(skipped, [])
        self.assertEqual(records[0]["sample_index"], 0)

    def test_no_usable_processed_samples_reports_every_skipped_row(self):
        entries = [{"line_number": i + 2, "distance_um": i, "kind": "peak"} for i in range(3)]
        for values in ([float("nan")] * 3, [], [None, float("inf"), -float("inf")]):
            with self.subTest(values=values):
                self.assertEqual(map_imported_points(
                    entries, [0, 1, 2], values, [(0, 0)] * 3, 0, "r", "data"
                ), ([], [2, 3, 4]))


if __name__ == "__main__":
    unittest.main()
