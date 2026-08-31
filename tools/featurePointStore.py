import uuid


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

    def replace_auto(self, profile_index, raster_layer_id, records):
        key = self._key(profile_index, raster_layer_id)
        manual = [item for item in self.records.get(key, []) if item["source"] == "manual"]
        manual_samples = {item["sample_index"] for item in manual}
        automatic = []
        seen = set()
        for source_record in records:
            record = dict(source_record)
            record["profile_index"] = profile_index
            record["raster_layer_id"] = raster_layer_id
            record["source"] = "auto"
            record.setdefault("id", uuid.uuid4().hex)
            identity = record["kind"], record["sample_index"]
            if record["sample_index"] in manual_samples or identity in seen:
                continue
            seen.add(identity)
            automatic.append(record)
        combined = manual + automatic
        combined.sort(key=lambda item: (item["sample_index"], item["kind"]))
        if combined:
            self.records[key] = combined
        else:
            self.records.pop(key, None)
        return list(combined)

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

