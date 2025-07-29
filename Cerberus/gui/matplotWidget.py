from typing import Dict, List
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator


class MatplotWidget(QWidget):
    def __init__(self, parent=None, title="", xlabel="", ylabel="", xlim=(0, 10), ylim=(0, 10)):
        super().__init__(parent)

        #self.figure = Figure(figsize=(5, 4), tight_layout=True)
        self.figure = Figure(figsize=(5, 4), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        # Initial settings
        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)

        self.ax.xaxis.set_major_locator(MultipleLocator(1))
        self.ax.yaxis.set_major_locator(MultipleLocator(1))
        self.ax.grid(True, which='major', axis='both', linestyle='--', linewidth=0.75, alpha=0.8)

        self.ax.xaxis.set_minor_locator(MultipleLocator(0.5))
        self.ax.yaxis.set_minor_locator(MultipleLocator(0.5))
        self.ax.grid(True, which='minor', axis='both', linestyle=':', linewidth=0.5, alpha=0.5)

        self.series_lines: Dict[str, Line2D] = {}  # name -> Line2D
        self.series_data: Dict[str, Dict[str, List]] = {}   # name -> {'x': [], 'y': []}

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def add_series(self, name, color=None):
        """Add an empty series to the plot."""
        line, = self.ax.plot([], [], marker='o', label=name, color=color)
        self.series_lines[name] = line
        self.series_data[name] = {'x': [], 'y': []}
        
        # Fix legend outside right-hand side
        self.ax.legend(
            loc='center left',
            bbox_to_anchor=(1.02, 0.5),
            borderaxespad=0.0)

        self.canvas.draw()
        self.figure.tight_layout()

    def append_point(self, name, x, y):
        """Add a single (x,y) point to a series."""
        if name not in self.series_data:
            raise ValueError(f"Series '{name}' not found.")

        self.series_data[name]['x'].append(x)
        self.series_data[name]['y'].append(y)

        line = self.series_lines[name]
        line.set_data(self.series_data[name]['x'], self.series_data[name]['y'])

        self.canvas.draw()
        self.figure.tight_layout()
