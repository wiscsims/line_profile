"""Range-aware Peak/Valley detection on raw profile-distance coordinates."""

import math

from .rangeUtils import merge_ranges


SCOPE_FULL_PROFILE = "full_profile"
SCOPE_SELECTED_RANGES = "selected_ranges"
SCOPE_CURRENT_MAP_EXTENT = "current_map_extent"


def full_profile_ranges(x_values):
    finite = [float(value) for value in x_values if value is not None and math.isfinite(float(value))]
    if len(finite) < 2:
        return []
    return [(min(finite), max(finite))]


def detect_in_ranges(detector, x_values, y_values, ranges, **options):
    """Detect independently in each raw-distance range.

    Slicing before invoking SciPy prevents excluded samples from affecting
    prominence, width, or Min distance.  Local sample indexes are restored to
    indexes in the complete processed profile before records are returned.
    """
    if len(x_values) != len(y_values):
        raise ValueError("Profile X/Y lengths do not match")

    combined = {"peak": [], "valley": []}
    for range_start, range_end in merge_ranges(ranges):
        indexes = [
            index
            for index, value in enumerate(x_values)
            if value is not None
            and math.isfinite(float(value))
            and range_start <= float(value) <= range_end
        ]
        if not indexes:
            continue
        first = indexes[0]
        last = indexes[-1] + 1
        scoped = detector.detect(x_values[first:last], y_values[first:last], **options)
        for kind in ("peak", "valley"):
            for source_record in scoped[kind]:
                record = dict(source_record)
                record["sample_index"] = first + record["sample_index"]
                combined[kind].append(record)
    for records in combined.values():
        records.sort(key=lambda record: record["sample_index"])
    return combined


def ranges_for_plot(ranges, converter):
    """Convert raw ranges only at rendering time."""
    return [(converter(start), converter(end)) for start, end in merge_ranges(ranges)]
