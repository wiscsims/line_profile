"""Pure UI-state decisions shared by the dock and focused unit tests."""


def peak_control_visibility(prominence_index, scope_index, algorithm):
    """Return which mode-dependent Peak Detection rows should be shown."""
    return {
        "adaptive_window": prominence_index > 0,
        "selected_ranges": scope_index == 1,
        "cwt_settings": algorithm == "cwt",
    }
