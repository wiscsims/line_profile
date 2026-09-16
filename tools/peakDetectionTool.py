import math


class PeakDetectionTool:
    """Numerical Peak/Valley detection with an optional SciPy dependency."""

    @staticmethod
    def scipy_available():
        try:
            from scipy.signal import find_peaks  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _scipy_functions():
        from scipy.ndimage import gaussian_filter1d
        from scipy.signal import find_peaks
        return find_peaks, gaussian_filter1d

    @staticmethod
    def _valid_runs(values):
        start = None
        for index, value in enumerate(values):
            is_valid = math.isfinite(value)
            if is_valid and start is None:
                start = index
            if start is not None and (not is_valid or index == len(values) - 1):
                end = index + 1 if is_valid and index == len(values) - 1 else index
                yield start, end
                start = None

    @staticmethod
    def _filter_by_profile_distance(candidates, min_distance):
        """Keep same-type candidates separated in physical profile distance.

        Candidates are considered in deterministic strength order: prominence,
        when SciPy supplied it, then detection-signal height, then ascending
        sample index.  This mirrors SciPy's stronger-feature preference while
        using actual profile coordinates rather than sample indexes.
        """
        if min_distance is None or min_distance <= 0:
            return candidates

        def strength(candidate):
            prominence = candidate["_prominence"]
            return (
                prominence is not None,
                prominence if prominence is not None else float("-inf"),
                candidate["_detection_height"],
                -candidate["sample_index"],
            )

        retained = []
        for candidate in sorted(candidates, key=strength, reverse=True):
            if all(
                abs(candidate["_profile_distance"] - other["_profile_distance"])
                >= min_distance
                for other in retained
            ):
                retained.append(candidate)
        return sorted(retained, key=lambda candidate: candidate["sample_index"])

    def detect(
        self,
        x,
        y,
        detect_peaks=True,
        detect_valleys=True,
        prominence=None,
        min_distance=None,
        width=None,
        smoothing_sigma=0.0,
    ):
        find_peaks, gaussian_filter1d = self._scipy_functions()
        raw_x = [float("nan") if value is None else float(value) for value in x]
        raw = [float("nan") if value is None else float(value) for value in y]
        if len(x) != len(raw):
            raise ValueError("Profile X/Y lengths do not match")

        options = {}
        if prominence is not None and prominence > 0:
            options["prominence"] = prominence
        if width is not None and width > 0:
            options["width"] = width

        results = {"peak": [], "valley": []}
        valid_values = [
            value if math.isfinite(value) and math.isfinite(raw_x[index]) else float("nan")
            for index, value in enumerate(raw)
        ]
        for start, end in self._valid_runs(valid_values):
            signal = list(raw[start:end])
            if smoothing_sigma and smoothing_sigma > 0:
                signal = list(gaussian_filter1d(signal, smoothing_sigma))
            kinds = []
            if detect_peaks:
                kinds.append(("peak", signal))
            if detect_valleys:
                kinds.append(("valley", [-value for value in signal]))
            for kind, detection_signal in kinds:
                indices, properties = find_peaks(detection_signal, **options)
                prominences = properties.get("prominences")
                widths = properties.get("widths")
                candidates = []
                for local_position, local_index in enumerate(indices):
                    sample_index = start + int(local_index)
                    candidates.append(
                        {
                            "kind": kind,
                            "sample_index": sample_index,
                            "distance": x[sample_index],
                            "value": y[sample_index],
                            "prominence": (
                                float(prominences[local_position]) if prominences is not None else None
                            ),
                            "width": float(widths[local_position]) if widths is not None else None,
                            "_profile_distance": raw_x[sample_index],
                            "_prominence": (
                                float(prominences[local_position]) if prominences is not None else None
                            ),
                            "_detection_height": float(detection_signal[local_index]),
                        }
                    )
                for candidate in self._filter_by_profile_distance(candidates, min_distance):
                    candidate.pop("_profile_distance")
                    candidate.pop("_prominence")
                    candidate.pop("_detection_height")
                    results[kind].append(candidate)
        return results

    @staticmethod
    def _snap(y, center_index, snap_range, find_maximum):
        values = [float("nan") if value is None else float(value) for value in y]
        if not values:
            return None
        center_index = max(0, min(int(center_index), len(values) - 1))
        snap_range = max(0, int(snap_range))
        start = max(0, center_index - snap_range)
        end = min(len(values), center_index + snap_range + 1)
        window = values[start:end]
        valid_indexes = [index for index, value in enumerate(window) if math.isfinite(value)]
        if not valid_indexes:
            return None
        selector = max if find_maximum else min
        local_index = selector(valid_indexes, key=lambda index: window[index])
        return start + local_index

    def snap_peak(self, y, center_index, snap_range):
        return self._snap(y, center_index, snap_range, True)

    def snap_valley(self, y, center_index, snap_range):
        return self._snap(y, center_index, snap_range, False)
