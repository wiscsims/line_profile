"""Shared, non-destructive processing for sampled profile data."""

import math


SMOOTHING_NONE = "none"
SMOOTHING_MOVING_AVERAGE = "moving_average"
SMOOTHING_GAUSSIAN = "gaussian"


def smoothing_mode(config):
    """Return a supported smoothing mode, including legacy configurations."""
    mode = config.get("smoothingMode")
    if mode in (SMOOTHING_NONE, SMOOTHING_MOVING_AVERAGE, SMOOTHING_GAUSSIAN):
        return mode
    return SMOOTHING_MOVING_AVERAGE if config.get("movingAverage") else SMOOTHING_NONE


def smoothing_signature(config):
    """Return the settings that change the processed profile values."""
    return (
        smoothing_mode(config),
        int(config.get("movingAverageN", 10)),
        float(config.get("gaussianSigmaUm", 0.0)),
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


def process_profile(
    data,
    config,
    gaussian_filter=None,
):
    """Return a same-length processed copy of ``data`` without mutating it.

    Moving-average and Gaussian filtering operate on finite runs independently,
    so missing samples remain hard boundaries rather than being bridged.
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
        spacings = [
            right - left
            for left, right in zip(run_x, run_x[1:])
            if math.isfinite(right - left) and right - left > 0
        ]
        if not spacings:
            raise ValueError("Gaussian smoothing requires positive profile spacing")
        spacings.sort()
        midpoint = len(spacings) // 2
        spacing = (
            spacings[midpoint]
            if len(spacings) % 2
            else (spacings[midpoint - 1] + spacings[midpoint]) / 2.0
        )
        result[start:end] = list(gaussian_filter(run_y, sigma_um / spacing))
    return list(raw_x), result
