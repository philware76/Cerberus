from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMainWindow
from PySide6.QtCore import Qt
import sys
import random


class TestStatus:
    NOT_TESTED = "not_tested"
    PASSED = "passed"
    FAILED = "failed"


def label_style(status: str):
    if status == TestStatus.NOT_TESTED:
        return {"bg": "black", "fg": "lime", "bold": False}
    elif status == TestStatus.PASSED:
        return {"bg": "lime", "fg": "black", "bold": False}
    elif status == TestStatus.FAILED:
        return {"bg": "#D32F2F", "fg": "black", "bold": False}
    else:
        return {"bg": "black", "fg": "lime", "bold": False}


class BandWidget(QWidget):
    def __init__(self, band_number: float, tx_status=TestStatus.NOT_TESTED, rx_status=TestStatus.NOT_TESTED):
        super().__init__()
        self.tx_label = QLabel("TX")
        self.tx_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.band_label = QLabel(f"{band_number}")
        self.band_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.rx_label = QLabel("RX")
        self.rx_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QHBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(0, 0, 0, 5)

        layout.addWidget(self.tx_label)
        layout.addWidget(self.band_label)
        layout.addWidget(self.rx_label)
        self.setLayout(layout)

        self.set_status(tx_status, rx_status)

        # Optional: Force fixed size for compact view
        self.setFixedHeight(30)
        self.setMinimumWidth(150)
        self.setStyleSheet("border: 1px solid red; background-color: black;")

    def apply_label_style(self, label: QLabel, status: str):
        style = label_style(status)
        bold_style = "font-weight: bold;" if style["bold"] else ""
        label.setStyleSheet(
            f"""
            background-color: {style['bg']}; 
            color: {style['fg']}; 
            padding: 0px; 
            margin: 0px; 
            border: 0px solid white; 
            font-size: 14px;
            {bold_style}
            """
        )

    def set_status(self, tx_status, rx_status):
        self.apply_label_style(self.tx_label, tx_status)
        self.apply_label_style(self.rx_label, rx_status)
        self.band_label.setStyleSheet("color: white; background-color: black; padding: 0px; border: 1px solid white; font-size: 12px;")


class BandListWidget(QWidget):
    def __init__(self, bands: list[int]):
        super().__init__()
        layout = QVBoxLayout()

        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Band Details", alignment=Qt.AlignmentFlag.AlignCenter))
        for band in bands:
            tx_status = random.choice([TestStatus.NOT_TESTED, TestStatus.PASSED, TestStatus.FAILED])
            rx_status = random.choice([TestStatus.NOT_TESTED, TestStatus.PASSED, TestStatus.FAILED])
            bandWidget: QWidget = BandWidget(band, tx_status, rx_status)
            layout.addWidget(bandWidget)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Band Details")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        band_numbers = [7, 20, 26, 8, 3, 25, 1, 77, 12, 28, 13, 40]
        band_list = BandListWidget(band_numbers)

        layout = QVBoxLayout()
        layout.addWidget(band_list, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        central_widget.setLayout(layout)
        self.setStyleSheet("background-color: #1e1e1e; color: white; font-size: 12pt;")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
