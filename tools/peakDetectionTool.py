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

    def detect(
        self,
        x,
        y,
        detect_peaks=True,
        detect_valleys=True,
        prominence=None,
        distance=None,
        width=None,
        smoothing_sigma=0.0,
    ):
        find_peaks, gaussian_filter1d = self._scipy_functions()
        raw = [float("nan") if value is None else float(value) for value in y]
        if len(x) != len(raw):
            raise ValueError("Profile X/Y lengths do not match")

        options = {}
        if prominence is not None and prominence > 0:
            options["prominence"] = prominence
        if distance is not None and distance > 1:
            options["distance"] = distance
        if width is not None and width > 0:
            options["width"] = width

        results = {"peak": [], "valley": []}
        for start, end in self._valid_runs(raw):
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
                for local_position, local_index in enumerate(indices):
                    sample_index = start + int(local_index)
                    results[kind].append(
                        {
                            "kind": kind,
                            "sample_index": sample_index,
                            "distance": x[sample_index],
                            "value": y[sample_index],
                            "prominence": (
                                float(prominences[local_position]) if prominences is not None else None
                            ),
                            "width": float(widths[local_position]) if widths is not None else None,
                        }
                    )
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
