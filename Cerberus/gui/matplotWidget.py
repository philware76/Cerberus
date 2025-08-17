from typing import Dict, List, Optional

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator
from PySide6.QtWidgets import QVBoxLayout, QWidget


class MatplotWidget(QWidget):
    def __init__(self,
                 parent=None,
                 title: str = "",
                 xlabel: str = "",
                 ylabel: str = "",
                 xlim=(0, 10),
                 ylim=(0, 10),
                 major_xtick: Optional[float] = None,
                 major_ytick: Optional[float] = None,
                 auto_ticks: bool = True):
        """Matplotlib embedded widget with optional auto tick spacing.

        If major_xtick / major_ytick not provided and auto_ticks=True, spacing is calculated
        to keep tick count reasonable (< ~30 major ticks) even for large spans (e.g. 100..3500).
        """
        super().__init__(parent)

        self.figure = Figure(figsize=(5, 4), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        # Initial settings
        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)

        # Configure ticks
        self._apply_tick_strategy(xlim, ylim, major_xtick, major_ytick, auto_ticks)

        self.series_lines: Dict[str, Line2D] = {}  # name -> Line2D
        self.series_data: Dict[str, Dict[str, List]] = {}   # name -> {'x': [], 'y': []}

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    # ---- Internal helpers ----
    def _nice_step(self, span: float) -> float:
        """Return a 'nice' step for the given span targeting ~10-15 ticks."""
        if span <= 0:
            return 1.0
        raw = span / 12.0  # target ~12 ticks
        magnitude = 10 ** int(len(str(int(raw))) - 1) if raw >= 1 else 1
        # Candidate set
        for m in [1, 2, 2.5, 5, 10]:
            step = m * magnitude
            if raw <= step:
                return step
        return 10 * magnitude

    def _apply_tick_strategy(self, xlim, ylim, major_xtick, major_ytick, auto_ticks):
        from math import ceil

        xspan = xlim[1] - xlim[0]
        yspan = ylim[1] - ylim[0]

        if auto_ticks:
            if major_xtick is None:
                major_xtick = self._nice_step(xspan)
            if major_ytick is None:
                major_ytick = self._nice_step(yspan)

        # Fallback protection: avoid > 1000 ticks
        def clamp(step, span):
            if step <= 0:
                return 1
            maxticks = span / step
            if maxticks > 1000:
                # Increase step
                factor = ceil(maxticks / 1000)
                return step * factor
            return step

        major_xtick = clamp(major_xtick, xspan) if major_xtick else 1
        major_ytick = clamp(major_ytick, yspan) if major_ytick else 1

        self.ax.xaxis.set_major_locator(MultipleLocator(major_xtick))
        self.ax.yaxis.set_major_locator(MultipleLocator(major_ytick))
        # Minor ticks: simple fraction (avoid flooding)
        if major_xtick > 1:
            self.ax.xaxis.set_minor_locator(MultipleLocator(major_xtick / 5))
        if major_ytick > 1:
            self.ax.yaxis.set_minor_locator(MultipleLocator(major_ytick / 5))

        self.ax.grid(True, which='major', axis='both', linestyle='--', linewidth=0.75, alpha=0.8)
        self.ax.grid(True, which='minor', axis='both', linestyle=':', linewidth=0.5, alpha=0.5)

    # ---- Public API ----
    def set_limits(self, xlim=None, ylim=None, *, auto_ticks: bool = True):
        """Dynamically update axis limits and (optionally) recompute tick spacing."""
        if xlim:
            self.ax.set_xlim(*xlim)
        if ylim:
            self.ax.set_ylim(*ylim)
        if auto_ticks and xlim and ylim:
            self._apply_tick_strategy(self.ax.get_xlim(), self.ax.get_ylim(), None, None, True)
        self.canvas.draw()

    def add_series(self, name, color=None, marker='o', marker_size: int = 4):
        """Add an empty series to the plot.

        marker_size: matplotlib 'markersize' (in points). Default smaller than original to avoid large blobs.
        """
        line, = self.ax.plot([], [], marker=marker, markersize=marker_size, label=name, color=color)
        self.series_lines[name] = line
        self.series_data[name] = {'x': [], 'y': []}

        # Fix legend outside right-hand side
        self.ax.legend(
            loc='center left',
            bbox_to_anchor=(1.02, 0.5),
            borderaxespad=0.0)

        self.canvas.draw()
        self.figure.tight_layout()

    def append_point(self, seriesName, x, y):
        """Add a single (x,y) point to a series."""
        if seriesName not in self.series_data:
            raise ValueError(f"Series '{seriesName}' not found.")

        self.series_data[seriesName]['x'].append(x)
        self.series_data[seriesName]['y'].append(y)

        line = self.series_lines[seriesName]
        line.set_data(self.series_data[seriesName]['x'], self.series_data[seriesName]['y'])

        self.canvas.draw()
        self.figure.tight_layout()
