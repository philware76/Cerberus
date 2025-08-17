"""
Run this example app like this:
py -m exampleCode.matplot 
"""
import random
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow

from Cerberus.gui.matplotWidget import MatplotWidget


class GraphTestApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live Updating Graph - One Series at a Time")
        self.resize(800, 600)

        self.graph = MatplotWidget(
            title="Sequentially Updating Series",
            xlabel="Time (s)",
            ylabel="Filtered Value",
            xlim=(0, 11),
            ylim=(0, 10)
        )
        self.setCentralWidget(self.graph)

        self.series_names = [f"Series {i+1}" for i in range(8)]
        self.current_series_index = 0
        self.max_points = 10
        self.current_point_index = 0

        self.series_state = {
            name: {
                'x': 0.0,
                'y': 5 + random.uniform(-1, 1)
            }
            for name in self.series_names
        }

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_next_point)
        self.timer.start(300)

    def update_next_point(self):
        if self.current_series_index >= len(self.series_names):
            self.timer.stop()
            return

        name = self.series_names[self.current_series_index]
        state = self.series_state[name]

        # Update x with small random delta (±0.2)
        delta_x = 1.0 + random.uniform(-0.05, 0.05)
        state['x'] += delta_x

        # Smooth y using exponential weighted average
        raw_y = random.uniform(0, 2)
        alpha = 0.3
        state['y'] = alpha * raw_y + (1 - alpha) * state['y']

        if not name in self.graph.series_data.keys():
            self.graph.add_series(name)

        self.graph.append_point(name, state['x'], state['y'])
        self.current_point_index += 1

        if self.current_point_index >= self.max_points:
            self.current_series_index += 1
            self.current_point_index = 0


def main():
    app = QApplication(sys.argv)
    window = GraphTestApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
