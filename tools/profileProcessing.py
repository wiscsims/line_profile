"""Shared, non-destructive processing for sampled profile data."""

import math


SMOOTHING_NONE = "none"
SMOOTHING_MOVING_AVERAGE = "moving_average"
SMOOTHING_GAUSSIAN = "gaussian"
SMOOTHING_SAVGOL = "savitzky_golay"


def smoothing_mode(config):
    """Return a supported smoothing mode, including legacy configurations."""
    mode = config.get("smoothingMode")
    if mode in (
        SMOOTHING_NONE,
        SMOOTHING_MOVING_AVERAGE,
        SMOOTHING_GAUSSIAN,
        SMOOTHING_SAVGOL,
    ):
        return mode
    return SMOOTHING_MOVING_AVERAGE if config.get("movingAverage") else SMOOTHING_NONE


def smoothing_signature(config):
    """Return the settings that change the processed profile values."""
    return (
        smoothing_mode(config),
        int(config.get("movingAverageN", 10)),
        float(config.get("gaussianSigmaUm", 0.0)),
        float(config.get("savgolWindowUm", 0.0)),
        int(config.get("savgolPolyOrder", 2)),
    )


def processed_data(descriptor):
    """Read processed data while remaining compatible with older descriptors."""
    return descriptor.get("processed_data", descriptor["data"])


def _finite_runs(x_values, y_values):
    start = None
    for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
        valid = math.isfinite(x_value) and math.isfinite(y_value)
        if valid and start is None:
            start = index
        if start is not None and (not valid or index == len(x_values) - 1):
            end = index + 1 if valid and index == len(x_values) - 1 else index
            yield start, end
            start = None


def _moving_average(values, window):
    """Centered moving average with NaN edges where no full window exists."""
    result = [float("nan")] * len(values)
    left = window // 2
    right = window - left - 1
    for index in range(left, len(values) - right):
        result[index] = sum(values[index - left:index + right + 1]) / window
    return result


def _gaussian_filter():
    from scipy.ndimage import gaussian_filter1d

    return gaussian_filter1d


def _savgol_filter():
    from scipy.signal import savgol_filter

    return savgol_filter


def _median_positive_spacing(x_values):
    spacings = [
        right - left
        for left, right in zip(x_values, x_values[1:])
        if math.isfinite(right - left) and right - left > 0
    ]
    if not spacings:
        return None
    spacings.sort()
    midpoint = len(spacings) // 2
    return (
        spacings[midpoint]
        if len(spacings) % 2
        else (spacings[midpoint - 1] + spacings[midpoint]) / 2.0
    )


def _nearest_savgol_window(requested_samples, polyorder, run_length):
    """Return the nearest valid odd sample length or ``None`` for short runs."""
    if requested_samples <= 0 or polyorder < 0:
        return None
    maximum = run_length if run_length % 2 else run_length - 1
    minimum = polyorder + 1
    if minimum % 2 == 0:
        minimum += 1
    if minimum > maximum:
        return None
    candidates = range(minimum, maximum + 1, 2)
    return min(candidates, key=lambda length: (abs(length - requested_samples), length))


def process_profile(
    data,
    config,
    gaussian_filter=None,
    savgol_filter=None,
):
    """Return a same-length processed copy of ``data`` without mutating it.

    Smoothing methods operate on finite runs independently, so missing samples
    remain hard boundaries rather than being bridged.
    """
    raw_x, raw_y = data
    if len(raw_x) != len(raw_y):
        raise ValueError("Profile X/Y lengths do not match")

    x_values = [float("nan") if value is None else float(value) for value in raw_x]
    y_values = [float("nan") if value is None else float(value) for value in raw_y]
    result = list(y_values)
    mode = smoothing_mode(config)

    if mode == SMOOTHING_NONE:
        return list(raw_x), result

    if mode == SMOOTHING_MOVING_AVERAGE:
        window = max(1, int(config.get("movingAverageN", 10)))
        for start, end in _finite_runs(x_values, y_values):
            result[start:end] = _moving_average(y_values[start:end], window)
        return list(raw_x), result

    if mode == SMOOTHING_SAVGOL:
        window_um = float(config.get("savgolWindowUm", 0.0))
        polyorder = int(config.get("savgolPolyOrder", 2))
        if window_um <= 0 or polyorder < 0:
            return list(raw_x), result
        if savgol_filter is None:
            savgol_filter = _savgol_filter()
        for start, end in _finite_runs(x_values, y_values):
            run_x = x_values[start:end]
            run_y = y_values[start:end]
            spacing = _median_positive_spacing(run_x)
            if spacing is None:
                continue
            window_length = _nearest_savgol_window(window_um / spacing, polyorder, len(run_y))
            if window_length is None:
                continue
            result[start:end] = list(
                savgol_filter(run_y, window_length, polyorder, mode="interp")
            )
        return list(raw_x), result

    sigma_um = float(config.get("gaussianSigmaUm", 0.0))
    if sigma_um <= 0:
        return list(raw_x), result
    if gaussian_filter is None:
        gaussian_filter = _gaussian_filter()

    for start, end in _finite_runs(x_values, y_values):
        run_x = x_values[start:end]
        run_y = y_values[start:end]
        if len(run_y) < 2:
            continue
        spacing = _median_positive_spacing(run_x)
        if spacing is None:
            raise ValueError("Gaussian smoothing requires positive profile spacing")
        result[start:end] = list(gaussian_filter(run_y, sigma_um / spacing))
    return list(raw_x), result
