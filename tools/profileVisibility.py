from qgis.core import QgsGeometry, QgsPointXY, QgsWkbTypes


def _line_parts(geometry):
    """Return all line parts from a QGIS intersection geometry."""
    if geometry is None or geometry.isEmpty():
        return []

    if QgsWkbTypes.geometryType(geometry.wkbType()) == QgsWkbTypes.LineGeometry:
        if geometry.isMultipart():
            return [part for part in geometry.asMultiPolyline() if len(part) >= 2]
        part = geometry.asPolyline()
        return [part] if len(part) >= 2 else []

    parts = []
    for child in geometry.asGeometryCollection():
        parts.extend(_line_parts(child))
    return parts


def _merge_ranges(ranges, tolerance=1e-9):
    """Merge only overlapping or immediately adjacent distance ranges."""
    merged = []
    for start, end in sorted(ranges):
        if end < start:
            start, end = end, start
        if end - start <= tolerance:
            continue
        if merged and start <= merged[-1][1] + tolerance:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def profile_visible_ranges(profile_line, extent):
    """Clip one profile to *extent* and return raw profile-distance ranges.

    Profile distances use each segment's ``distance_pixel_sized`` value, which
    is the same raw distance coordinate used by the sampled profile data.
    """
    if not profile_line or extent is None or extent.isEmpty():
        return []

    extent_geometry = QgsGeometry.fromRect(extent)
    ranges = []
    cumulative_distance = 0.0

    for segment in profile_line:
        segment_distance = float(segment.get("distance_pixel_sized", 0.0))
        map_distance = float(segment.get("distance", 0.0))
        if segment_distance <= 0 or map_distance <= 0:
            cumulative_distance += max(segment_distance, 0.0)
            continue

        start = QgsPointXY(*segment["start"])
        end = QgsPointXY(*segment["end"])
        segment_geometry = QgsGeometry.fromPolylineXY([start, end])
        clipped = segment_geometry.intersection(extent_geometry)

        for part in _line_parts(clipped):
            located = []
            for point in (part[0], part[-1]):
                distance_on_segment = segment_geometry.lineLocatePoint(
                    QgsGeometry.fromPointXY(QgsPointXY(point))
                )
                if distance_on_segment >= 0:
                    fraction = min(1.0, max(0.0, distance_on_segment / map_distance))
                    located.append(cumulative_distance + fraction * segment_distance)
            if len(located) == 2:
                ranges.append((min(located), max(located)))

        cumulative_distance += segment_distance

    return _merge_ranges(ranges)


def visible_profile_ranges(profile_lines, extent):
    """Return independent raw visible ranges for every profile index."""
    return {
        profile_index: profile_visible_ranges(profile_line, extent)
        for profile_index, profile_line in enumerate(profile_lines)
    }


def distance_in_ranges(distance, ranges, tolerance=1e-9):
    return any(start - tolerance <= distance <= end + tolerance for start, end in ranges)
