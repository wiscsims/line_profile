import importlib
import os
import sys
import sysconfig

from qgis.PyQt.QtCore import QProcess, Qt
from qgis.PyQt.QtWidgets import QMessageBox, QProgressDialog
from qgis.core import QgsApplication


class SciPyDependencyManager:
    """Install optional SciPy into the active QGIS user's profile."""

    def __init__(self):
        self.process = None
        self.progress = None
        self.success_callback = None
        self.prefix = None
        self.install_cancelled = False

    @staticmethod
    def has_scipy():
        try:
            from scipy.signal import find_peaks  # noqa: F401
            return True
        except ImportError:
            return False

    def ensure_scipy(self, parent, success_callback=None):
        if self.has_scipy():
            if success_callback:
                success_callback()
            return True

        response = QMessageBox.question(
            parent,
            "SciPy dependency",
            "Gaussian and Savitzky–Golay profile smoothing and Peak/Valley auto detection require SciPy.\n\n"
            "SciPy is not available in the Python environment used by QGIS. "
            "Install SciPy for the current QGIS user profile now?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if response != QMessageBox.Yes:
            return False
        self.install_scipy(parent, success_callback)
        return False

    def install_scipy(self, parent, success_callback=None):
        self.success_callback = success_callback
        self.install_cancelled = False
        self.prefix = os.path.join(QgsApplication.qgisSettingsDirPath(), "python", "dependencies")
        try:
            os.makedirs(self.prefix, exist_ok=True)
        except OSError as error:
            QMessageBox.critical(parent, "SciPy dependency", str(error))
            return

        self.progress = QProgressDialog("Installing SciPy…", "Cancel", 0, 0, parent)
        self.progress.setWindowTitle("SciPy dependency")
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setMinimumDuration(0)

        self.process = QProcess(parent)
        self.process.setProgram(sys.executable)
        self.process.setArguments(
            [
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--prefix",
                self.prefix,
                "scipy",
            ]
        )
        self.process.finished.connect(lambda exit_code, exit_status: self._finished(parent, exit_code))
        self.progress.canceled.connect(self._cancel_install)
        self.process.start()

    def _cancel_install(self):
        self.install_cancelled = True
        if self.process is not None:
            self.process.kill()

    def _site_paths(self):
        variables = {
            "base": self.prefix,
            "platbase": self.prefix,
            "installed_base": self.prefix,
            "installed_platbase": self.prefix,
        }
        scheme = "nt" if os.name == "nt" else "posix_prefix"
        paths = sysconfig.get_paths(scheme=scheme, vars=variables)
        return [paths[name] for name in ("purelib", "platlib") if paths.get(name)]

    def _finished(self, parent, exit_code):
        stdout = bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace")
        stderr = bytes(self.process.readAllStandardError()).decode("utf-8", "replace")
        if self.progress:
            self.progress.close()

        if self.install_cancelled:
            self._clear_process_state()
            return

        if exit_code == 0:
            for path in self._site_paths():
                if path not in sys.path:
                    sys.path.insert(0, path)
            importlib.invalidate_caches()
            if self.has_scipy():
                QMessageBox.information(parent, "SciPy dependency", "SciPy was installed successfully.")
                callback = self.success_callback
                self._clear_process_state()
                if callback:
                    callback()
                return

        message = QMessageBox(parent)
        message.setIcon(QMessageBox.Critical)
        message.setWindowTitle("SciPy dependency")
        message.setText("SciPy could not be installed. Gaussian and Savitzky–Golay smoothing and automatic Peak/Valley detection are unavailable.")
        message.setDetailedText((stderr or stdout or "pip returned no diagnostic output").strip())
        message.exec_()
        self._clear_process_state()

    def _clear_process_state(self):
        self.process = None
        self.progress = None
        self.success_callback = None
        self.install_cancelled = False
