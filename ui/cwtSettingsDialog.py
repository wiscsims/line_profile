"""Compact, layout-driven settings for the CWT candidate finder."""

from qgis.PyQt.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QMessageBox, QSpinBox,
)

from ..tools.peakDetectionTool import PeakDetectionTool


class CwtSettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CWT Settings")
        layout = QFormLayout(self)
        self.fields = {}
        for key, label, tooltip in (
            ("cwt_min_scale", "Minimum scale [µm]",
             "Smallest Ricker wavelet scale in raw profile µm, not the measured peak width. "
             "Divided by median positive sample spacing within each finite scope interval."),
            ("cwt_max_scale", "Maximum scale [µm]",
             "Largest Ricker wavelet scale in raw profile µm. Must be at least Minimum scale."),
            ("cwt_num_scales", "Number of scales",
             "Number of linearly spaced scales from Minimum to Maximum, including both endpoints (2–512)."),
            ("cwt_min_snr", "Minimum SNR",
             "Dimensionless signal-to-noise threshold for SciPy CWT ridge selection. "
             "Higher values reject more candidate ridges; 0 disables this threshold."),
        ):
            if key == "cwt_num_scales":
                field = QSpinBox(self)
                field.setRange(2, 512)
            else:
                field = QDoubleSpinBox(self)
                field.setDecimals(3)
                field.setRange(0 if key == "cwt_min_snr" else 0.001, 999999)
            field.setObjectName(key)
            field.setToolTip(tooltip)
            field.setValue(settings[key])
            self.fields[key] = field
            layout.addRow(label, field)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def settings(self):
        return {key: field.value() for key, field in self.fields.items()}

    def accept(self):
        try:
            PeakDetectionTool.validate_cwt_settings(self.settings())
        except ValueError as error:
            QMessageBox.warning(self, "CWT Settings", str(error))
            return
        super().accept()
