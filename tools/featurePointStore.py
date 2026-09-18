import uuid

from .rangeUtils import distance_in_ranges, merge_ranges


class FeaturePointStore:
    """Authoritative, graphics-independent Peak/Valley record store."""

    def __init__(self):
        self.records = {}

    @staticmethod
    def _key(profile_index, raster_layer_id):
        return profile_index, raster_layer_id

    def records_for(self, profile_index, raster_layer_id):
        return list(self.records.get(self._key(profile_index, raster_layer_id), []))

    def keys(self):
        return list(self.records.keys())

    def all_records(self):
        records = []
        for key_records in self.records.values():
            records.extend(key_records)
        return list(records)

    def add_manual(self, record):
        record = dict(record)
        record["source"] = "manual"
        record.setdefault("id", uuid.uuid4().hex)
        key = self._key(record["profile_index"], record["raster_layer_id"])
        key_records = self.records.setdefault(key, [])
        sample_index = record["sample_index"]

        same = [item for item in key_records if item["sample_index"] == sample_index]
        if len(same) == 1 and same[0]["kind"] == record["kind"] and same[0]["source"] == "manual":
            return same[0]

        key_records[:] = [item for item in key_records if item["sample_index"] != sample_index]
        key_records.append(record)
        key_records.sort(key=lambda item: (item["sample_index"], item["kind"]))
        return record

    def add_imported(self, record):
        """Add an imported record without duplicating its current sample/type."""
        record = dict(record)
        record["source"] = "imported"
        record.setdefault("id", uuid.uuid4().hex)
        key = self._key(record["profile_index"], record["raster_layer_id"])
        key_records = self.records.setdefault(key, [])
        sample_index = record["sample_index"]

        same = [item for item in key_records if item["sample_index"] == sample_index]
        if len(same) == 1 and same[0]["kind"] == record["kind"]:
            return same[0]

        key_records[:] = [item for item in key_records if item["sample_index"] != sample_index]
        key_records.append(record)
        key_records.sort(key=lambda item: (item["sample_index"], item["kind"]))
        return record

    def replace_auto(self, profile_index, raster_layer_id, records):
        key = self._key(profile_index, raster_layer_id)
        curated = [item for item in self.records.get(key, []) if item["source"] != "auto"]
        curated_samples = {item["sample_index"] for item in curated}
        automatic = []
        seen = set()
        for source_record in records:
            record = dict(source_record)
            record["profile_index"] = profile_index
            record["raster_layer_id"] = raster_layer_id
            record["source"] = "auto"
            record.setdefault("id", uuid.uuid4().hex)
            identity = record["kind"], record["sample_index"]
            if record["sample_index"] in curated_samples or identity in seen:
                continue
            seen.add(identity)
            automatic.append(record)
        combined = curated + automatic
        combined.sort(key=lambda item: (item["sample_index"], item["kind"]))
        if combined:
            self.records[key] = combined
        else:
            self.records.pop(key, None)
        return list(combined)

    def records_in_ranges(self, profile_index, raster_layer_id, ranges):
        ranges = merge_ranges(ranges)
        return [
            item
            for item in self.records_for(profile_index, raster_layer_id)
            if distance_in_ranges(item["distance"], ranges)
        ]

    def replace_auto_in_ranges(self, profile_index, raster_layer_id, records, ranges):
        """Replace all automatic records with results from the supplied raw µm ranges."""
        ranges = merge_ranges(ranges)
        key = self._key(profile_index, raster_layer_id)
        existing = self.records.get(key, [])
        retained = [item for item in existing if item["source"] != "auto"]
        curated_samples = {
            item["sample_index"] for item in existing if item["source"] != "auto"
        }
        seen = set()
        for source_record in records:
            if not distance_in_ranges(source_record["distance"], ranges):
                continue
            record = dict(source_record)
            record["profile_index"] = profile_index
            record["raster_layer_id"] = raster_layer_id
            record["source"] = "auto"
            record.setdefault("id", uuid.uuid4().hex)
            identity = record["kind"], record["sample_index"]
            if record["sample_index"] in curated_samples or identity in seen:
                continue
            seen.add(identity)
            retained.append(record)
        retained.sort(key=lambda item: (item["sample_index"], item["kind"]))
        if retained:
            self.records[key] = retained
        else:
            self.records.pop(key, None)
        return list(retained)

    def clear_in_ranges(
        self,
        profile_index,
        raster_layer_id,
        ranges,
        include_curated=False,
    ):
        """Remove records inside raw µm ranges, optionally including curated points."""
        ranges = merge_ranges(ranges)
        key = self._key(profile_index, raster_layer_id)
        removed = []
        retained = []
        for item in self.records.get(key, []):
            in_scope = distance_in_ranges(item["distance"], ranges)
            removable = item["source"] == "auto" or include_curated
            if in_scope and removable:
                removed.append(item)
            else:
                retained.append(item)
        if retained:
            self.records[key] = retained
        else:
            self.records.pop(key, None)
        return removed

    def clear_auto(self, profile_index, raster_layer_id):
        key = self._key(profile_index, raster_layer_id)
        remaining = [item for item in self.records.get(key, []) if item["source"] != "auto"]
        if remaining:
            self.records[key] = remaining
        else:
            self.records.pop(key, None)

    def clear_key(self, profile_index, raster_layer_id):
        self.records.pop(self._key(profile_index, raster_layer_id), None)

    def clear_profile(self, profile_index):
        for key in [key for key in self.records if key[0] == profile_index]:
            self.records.pop(key, None)

    def clear_all(self):
        self.records.clear()

    def delete_nearest(self, profile_index, raster_layer_id, sample_index, tolerance):
        key = self._key(profile_index, raster_layer_id)
        key_records = self.records.get(key, [])
        if not key_records:
            return None
        nearest = min(key_records, key=lambda item: abs(item["sample_index"] - sample_index))
        if abs(nearest["sample_index"] - sample_index) > tolerance:
            return None
        key_records.remove(nearest)
        if not key_records:
            self.records.pop(key, None)
        return nearest
