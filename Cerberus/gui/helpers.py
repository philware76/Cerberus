from threading import Lock
from typing import Dict, Optional, cast

from PySide6.QtCore import QEventLoop, Qt
from PySide6.QtWidgets import (QApplication, QDialog, QPushButton, QVBoxLayout,
                               QWidget)

from Cerberus.gui.matplotWidget import MatplotWidget
from Cerberus.gui.widgetGen import apply_parameters, create_all_parameters_ui
from Cerberus.plugins.baseParameters import BaseParameters


def _ensure_qapp() -> QApplication:
    """Return existing QApplication or create one, and configure it not to quit on last window.

    Guard attribute access for environments where the instance might be a
    generic QCoreApplication (rare in this context, but keeps static checkers happy).
    """
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication([])
    qapp = cast(QApplication, inst)
    if hasattr(qapp, "setQuitOnLastWindowClosed"):
        qapp.setQuitOnLastWindowClosed(False)
    return qapp


def displayWidget(widget: QWidget):
    qapp = _ensure_qapp()

    window = QWidget()
    layout = QVBoxLayout(window)

    layout.addWidget(widget)

    window.setWindowTitle("Widget")
    window.resize(400, 300)
    window.show()

    # Block with local loop so other global windows (e.g., persistent plot) remain intact.
    loop = QEventLoop()

    def on_close():
        if loop.isRunning():
            loop.quit()

    window.destroyed.connect(on_close)
    loop.exec()


def displayParametersUI(pluginName: str, groups: Dict[str, BaseParameters], *, close_on_apply: bool = True):
    """Show a modal Parameters dialog without terminating the global QApplication.

    Uses QDialog.exec() (its own local loop). The dialog appears in the Windows
    taskbar grouped under the application's main icon. Windows will not create a
    separate new taskbar icon for the same process unless a distinct AppUserModelID
    or separate process is used.
    """
    _ensure_qapp()

    dialog = QDialog()
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    # Ensure treated as a top-level window with a normal entry
    dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.Window)

    layout = QVBoxLayout(dialog)
    ui, widget_map = create_all_parameters_ui(groups)
    layout.addWidget(ui)

    apply_btn = QPushButton("Apply")
    layout.addWidget(apply_btn)

    def on_apply():
        apply_parameters(groups, widget_map)
        print("Updated parameters:")
        for group in groups.values():
            for param in group.values():
                print(f"{group.groupName} -> {param.name}: {param.value} {param.units}")
        if close_on_apply:
            dialog.accept()

    apply_btn.clicked.connect(on_apply)

    dialog.setWindowTitle(f"{pluginName} Parameters")
    dialog.resize(420, 340)
    dialog.exec()


# ---------------------- Persistent / Global MatPlot UI Support ---------------------- #
class GlobalMatPlotUI:
    """A lightweight singleton-like context to keep a MatplotWidget window
    open across multiple test runs and add a new data series each time.

    Interim hack until a proper GUI hosts these widgets. We simply keep a
    single window alive; each test run adds a new series. UI responsiveness
    is maintained by calling processEvents() after each appended point.
    """

    _instance: Optional["GlobalMatPlotUI"] = None

    def __init__(self,
                 title: str,
                 xlabel: str,
                 ylabel: str,
                 *,
                 xlim: tuple[float, float],
                 ylim: tuple[float, float],
                 window_title: str,
                 width: int = 800,
                 height: int = 500):

        # Reuse or create the shared QApplication instance
        self.qapp = _ensure_qapp()

        self.window = QWidget()
        layout = QVBoxLayout(self.window)

        self.matplot = MatplotWidget(
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            xlim=xlim,
            ylim=ylim
        )
        layout.addWidget(self.matplot)

        self.window.setWindowTitle(window_title)
        self.window.resize(width, height)
        self.window.show()

        # Internal state
        self._series_counter = 0
        self._lock = Lock()

    # ---------------------- public API ---------------------- #
    def new_series(self, base_name: str) -> str:
        with self._lock:
            self._series_counter += 1
            name = f"{base_name}{self._series_counter}"
            if name not in self.matplot.series_data:
                self.matplot.add_series(name)
            return name

    def append_point(self, series: str, x: float, y: float):
        # Series must exist; if not create it (defensive)
        if series not in self.matplot.series_data:
            self.matplot.add_series(series)
        self.matplot.append_point(series, x, y)
        # Pump events to keep window responsive.
        self.qapp.processEvents()

    def update_axes_ranges(self, xlim: tuple[float, float], ylim: tuple[float, float]):
        # Expand (not shrink) existing ranges so previous data remains visible
        ax = self.matplot.ax
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        new_xlim = (min(cur_xlim[0], xlim[0]), max(cur_xlim[1], xlim[1]))
        new_ylim = (min(cur_ylim[0], ylim[0]), max(cur_ylim[1], ylim[1]))
        ax.set_xlim(new_xlim)
        ax.set_ylim(new_ylim)
        self.matplot.canvas.draw_idle()

    @classmethod
    def get(cls,
            *,
            title: str,
            xlabel: str,
            ylabel: str,
            xlim: tuple[float, float],
            ylim: tuple[float, float],
            window_title: str = "Matplot Window") -> "GlobalMatPlotUI":
        if cls._instance is None:
            cls._instance = cls(title, xlabel, ylabel,
                                xlim=xlim, ylim=ylim, window_title=window_title)
        else:
            # Update axes if needed (only expand)
            cls._instance.update_axes_ranges(xlim, ylim)
        return cls._instance


def getGlobalMatPlotUI(*,
                       title: str,
                       xlabel: str,
                       ylabel: str,
                       xlim: tuple[float, float],
                       ylim: tuple[float, float],
                       window_title: str = "Matplot Window") -> GlobalMatPlotUI:
    """Convenience wrapper to obtain the persistent GlobalMatPlotUI.

    Creates it on first call; afterwards returns the existing instance and
    expands axes limits if the requested ranges exceed current ones.
    """
    return GlobalMatPlotUI.get(title=title, xlabel=xlabel, ylabel=ylabel,
                               xlim=xlim, ylim=ylim, window_title=window_title)
