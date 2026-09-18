"""Reusable helpers for raw physical profile-distance ranges."""

import math
import re


def merge_ranges(ranges, tolerance=1e-9):
    """Normalize and merge overlapping or immediately adjacent ranges."""
    normalized = []
    for start, end in ranges:
        start = float(start)
        end = float(end)
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError("Detection ranges must contain finite distances")
        if end < start:
            start, end = end, start
        if end - start > tolerance:
            normalized.append((start, end))

    merged = []
    for start, end in sorted(normalized):
        if merged and start <= merged[-1][1] + tolerance:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def distance_in_ranges(distance, ranges, tolerance=1e-9):
    return any(start - tolerance <= distance <= end + tolerance for start, end in ranges)


def parse_ranges(text):
    """Parse ``start-end; start-end`` ranges expressed in raw µm."""
    if not text or not text.strip():
        return []
    ranges = []
    for item in text.split(";"):
        values = re.split(r"\s*(?:-|–|:|,)\s*", item.strip())
        if len(values) != 2 or not all(values):
            raise ValueError("Use start-end pairs separated by semicolons")
        ranges.append((float(values[0]), float(values[1])))
    return merge_ranges(ranges)


def format_ranges(ranges):
    return "; ".join("{:g}-{:g}".format(start, end) for start, end in merge_ranges(ranges))
