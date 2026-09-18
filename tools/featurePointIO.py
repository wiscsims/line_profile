"""Delimited-file import and export helpers for Peak / Valley records."""

import csv
import math
import os


EXPORT_FIELDS = (
    "type",
    "source",
    "profile",
    "data",
    "distance_um",
    "value",
    "sample_index",
    "prominence",
    "width_um",
    "map_x",
    "map_y",
)


def delimiter_for_path(path):
    return "\t" if os.path.splitext(path)[1].lower() == ".tsv" else ","


def point_coordinates(point):
    if hasattr(point, "x") and callable(point.x):
        return point.x(), point.y()
    return point[0], point[1]


def csv_value(value):
    return "" if value is None or (isinstance(value, float) and not math.isfinite(value)) else value


def export_feature_points(path, records):
    """Write portable Peak / Valley records and return the number of rows."""
    with open(path, "w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS, delimiter=delimiter_for_path(path))
        writer.writeheader()
        for record in records:
            map_x, map_y = point_coordinates(record["point"])
            writer.writerow(
                {
                    "type": record["kind"],
                    "source": record["source"],
                    "profile": record["profile_index"] + 1,
                    "data": record.get("data_label", ""),
                    "distance_um": csv_value(record["distance"]),
                    "value": csv_value(record["value"]),
                    "sample_index": record["sample_index"],
                    "prominence": csv_value(record.get("prominence")),
                    "width_um": csv_value(record.get("width")),
                    "map_x": csv_value(map_x),
                    "map_y": csv_value(map_y),
                }
            )
    return len(records)


def read_delimited_rows(path):
    """Read CSV, TSV, or TXT rows while retaining physical file line numbers."""
    with open(path, newline="", encoding="utf-8-sig") as source:
        sample = source.read(4096)
        source.seek(0)
        delimiter = delimiter_for_path(path)
        if os.path.splitext(path)[1].lower() == ".txt":
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;").delimiter
            except csv.Error:
                pass
        reader = csv.DictReader(source, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("The file has no header row.")
        headers = {header.strip().lower() for header in reader.fieldnames if header}
        rows = []
        for line_number, row in enumerate(reader, start=2):
            rows.append(
                (
                    line_number,
                    {
                        key.strip().lower(): (value.strip() if isinstance(value, str) else "")
                        for key, value in row.items()
                        if key is not None
                    },
                )
            )
    return headers, rows


def parse_import_rows(rows, default_type=None):
    """Validate portable/minimal rows, returning entries and skipped line numbers."""
    parsed = []
    skipped = []
    for line_number, row in rows:
        try:
            distance = float(row.get("distance_um", ""))
        except (TypeError, ValueError):
            skipped.append(line_number)
            continue
        kind = (row.get("type") or default_type or "").strip().lower()
        if not math.isfinite(distance) or kind not in ("peak", "valley"):
            skipped.append(line_number)
            continue
        parsed.append({"line_number": line_number, "distance_um": distance, "kind": kind})
    return parsed, skipped


def map_imported_points(entries, x_values, y_values, centers, profile_index, raster_layer_id, data_label):
    """Snap within the full raw extent to finite processed samples with map positions."""
    finite_indexes = [
        index for index, value in enumerate(x_values) if isinstance(value, (int, float)) and math.isfinite(value)
    ]
    if not finite_indexes:
        return [], [entry["line_number"] for entry in entries]
    minimum = min(x_values[index] for index in finite_indexes)
    maximum = max(x_values[index] for index in finite_indexes)
    eligible_indexes = []
    for index in finite_indexes:
        if index >= len(y_values) or index >= len(centers):
            continue
        try:
            map_x, map_y = point_coordinates(centers[index])
            usable = all(math.isfinite(value) for value in (y_values[index], map_x, map_y))
        except (TypeError, ValueError, IndexError, AttributeError):
            usable = False
        if usable:
            eligible_indexes.append(index)
    if not eligible_indexes:
        return [], [entry["line_number"] for entry in entries]
    records = []
    skipped = []
    for entry in entries:
        distance = entry["distance_um"]
        if distance < minimum or distance > maximum:
            skipped.append(entry["line_number"])
            continue
        sample_index = min(eligible_indexes, key=lambda index: abs(x_values[index] - distance))
        records.append(
            {
                "kind": entry["kind"],
                "source": "imported",
                "profile_index": profile_index,
                "raster_layer_id": raster_layer_id,
                "sample_index": sample_index,
                "distance": x_values[sample_index],
                "value": y_values[sample_index],
                "point": centers[sample_index],
                "prominence": None,
                "width": None,
                "data_label": data_label,
            }
        )
    return records, skipped
