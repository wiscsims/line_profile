import math


PROMINENCE_ABSOLUTE = "absolute"
PROMINENCE_LOCAL_RANGE = "local_range_percent"
PROMINENCE_LOCAL_SD = "local_sd"
PROMINENCE_LOCAL_MAD = "local_mad"


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
        from scipy.signal import find_peaks
        return find_peaks

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

    @staticmethod
    def _interpolate_profile_x(x_values, sample_position):
        """Convert a SciPy fractional sample position to physical profile x."""
        if not x_values or not math.isfinite(sample_position):
            return None
        position = min(max(float(sample_position), 0.0), len(x_values) - 1.0)
        left_index = int(math.floor(position))
        right_index = min(left_index + 1, len(x_values) - 1)
        fraction = position - left_index
        return x_values[left_index] + fraction * (x_values[right_index] - x_values[left_index])

    @staticmethod
    def _median(values):
        ordered = sorted(values)
        middle = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[middle]
        return (ordered[middle - 1] + ordered[middle]) / 2.0

    @classmethod
    def _prominence_threshold(
        cls,
        candidate,
        run_x,
        run_y,
        prominence_mode,
        prominence,
        prominence_window,
    ):
        value = float(prominence or 0.0)
        if prominence_mode == PROMINENCE_ABSOLUTE:
            return value
        if prominence_mode not in (
            PROMINENCE_LOCAL_RANGE,
            PROMINENCE_LOCAL_SD,
            PROMINENCE_LOCAL_MAD,
        ):
            raise ValueError("Unknown prominence mode: {}".format(prominence_mode))
        if value <= 0:
            return 0.0
        if prominence_window is None or prominence_window <= 0:
            raise ValueError("Adaptive prominence Window must be greater than 0 µm.")

        center_x = run_x[candidate["_run_index"]]
        half_window = float(prominence_window) / 2.0
        local_values = [
            y_value
            for x_value, y_value in zip(run_x, run_y)
            if abs(x_value - center_x) <= half_window
        ]
        if not local_values:
            return 0.0
        if prominence_mode == PROMINENCE_LOCAL_RANGE:
            return (max(local_values) - min(local_values)) * value / 100.0
        if prominence_mode == PROMINENCE_LOCAL_SD:
            mean = sum(local_values) / len(local_values)
            standard_deviation = math.sqrt(
                sum((item - mean) ** 2 for item in local_values) / len(local_values)
            )
            return value * standard_deviation
        median = cls._median(local_values)
        mad = cls._median([abs(item - median) for item in local_values])
        return value * 1.4826 * mad

    def filter_candidates(
        self,
        candidates,
        run_x,
        run_y,
        prominence_mode=PROMINENCE_ABSOLUTE,
        prominence=None,
        prominence_window=None,
        min_width=None,
        min_distance=None,
    ):
        """Apply finder-independent prominence, width, and distance filters."""
        retained = []
        for candidate in candidates:
            threshold = self._prominence_threshold(
                candidate,
                run_x,
                run_y,
                prominence_mode,
                prominence,
                prominence_window,
            )
            measured = candidate["prominence"]
            if threshold > 0 and (measured is None or measured < threshold):
                continue
            retained.append(candidate)

        if min_width is not None and min_width > 0:
            retained = [
                candidate
                for candidate in retained
                if candidate["width"] is not None and candidate["width"] >= min_width
            ]
        return self._filter_by_profile_distance(retained, min_distance)

    def detect(
        self,
        x,
        y,
        detect_peaks=True,
        detect_valleys=True,
        prominence=None,
        prominence_mode=PROMINENCE_ABSOLUTE,
        prominence_window=None,
        min_distance=None,
        min_width=None,
    ):
        find_peaks = self._scipy_functions()
        raw_x = [float("nan") if value is None else float(value) for value in x]
        raw = [float("nan") if value is None else float(value) for value in y]
        if len(x) != len(raw):
            raise ValueError("Profile X/Y lengths do not match")

        # Ask the candidate finder to calculate properties without applying
        # thresholds.  All filtering is performed in the common stage below.
        options = {"prominence": (None, None), "width": (None, None)}

        results = {"peak": [], "valley": []}
        valid_values = [
            value if math.isfinite(value) and math.isfinite(raw_x[index]) else float("nan")
            for index, value in enumerate(raw)
        ]
        for start, end in self._valid_runs(valid_values):
            signal = list(raw[start:end])
            run_x = raw_x[start:end]
            kinds = []
            if detect_peaks:
                kinds.append(("peak", signal))
            if detect_valleys:
                kinds.append(("valley", [-value for value in signal]))
            for kind, detection_signal in kinds:
                indices, properties = find_peaks(detection_signal, **options)
                prominences = properties.get("prominences")
                widths = properties.get("widths")
                left_ips = properties.get("left_ips")
                right_ips = properties.get("right_ips")
                candidates = []
                for local_position, local_index in enumerate(indices):
                    sample_index = start + int(local_index)
                    width_um = None
                    if widths is not None and left_ips is not None and right_ips is not None:
                        left_x = self._interpolate_profile_x(
                            raw_x[start:end], left_ips[local_position]
                        )
                        right_x = self._interpolate_profile_x(
                            raw_x[start:end], right_ips[local_position]
                        )
                        if left_x is not None and right_x is not None:
                            width_um = abs(right_x - left_x)
                    candidates.append(
                        {
                            "kind": kind,
                            "sample_index": sample_index,
                            "distance": x[sample_index],
                            "value": y[sample_index],
                            "prominence": (
                                float(prominences[local_position]) if prominences is not None else None
                            ),
                            "width": width_um,
                            "_profile_distance": raw_x[sample_index],
                            "_prominence": (
                                float(prominences[local_position])
                                if prominences is not None and prominence is not None and prominence > 0
                                else None
                            ),
                            "_detection_height": float(detection_signal[local_index]),
                            "_run_index": int(local_index),
                        }
                    )
                filtered = self.filter_candidates(
                    candidates,
                    run_x,
                    signal,
                    prominence_mode=prominence_mode,
                    prominence=prominence,
                    prominence_window=prominence_window,
                    min_width=min_width,
                    min_distance=min_distance,
                )
                for candidate in filtered:
                    candidate.pop("_profile_distance")
                    candidate.pop("_prominence")
                    candidate.pop("_detection_height")
                    candidate.pop("_run_index")
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
