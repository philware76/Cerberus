import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QHBoxLayout, QToolButton, QFrame
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve


class CollapsibleGroupBox(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        # === Toggle button ===
        self.toggle_button = QToolButton()
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toggle_button.setArrowType(Qt.DownArrow)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.setFixedSize(16, 16)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")

        # === Header label ===
        self.header_label = QLabel(title)
        self.header_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                padding: 2px 6px;
            }
        """)

        # === Header layout ===
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(6, 2, 6, 2)
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_button)

        self.header_frame = QFrame()
        self.header_frame.setLayout(header_layout)
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #2A6099;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
        """)

        # === Content Area ===
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.StyledPanel)
        self.content_area.setStyleSheet("""
            QFrame {
                background-color: #D6EAF8;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
        """)
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(10, 8, 10, 10)
        self.content_layout.setSpacing(6)
        self.content_area.setLayout(self.content_layout)

        # === Animation ===
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        # === Main layout ===
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.header_frame)
        main_layout.addWidget(self.content_area)
        self.setLayout(main_layout)

        # === Connections ===
        self.toggle_button.clicked.connect(self.toggle_content)

        # === Initialize state ===
        if self.toggle_button.isChecked():
            self.content_area.setVisible(True)
            self.content_area.setMaximumHeight(self.content_area.sizeHint().height())
        else:
            self.content_area.setVisible(False)
            self.content_area.setMaximumHeight(0)

    def toggle_content(self):
        expanding = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if expanding else Qt.RightArrow)

        if expanding:
            self.content_area.setVisible(True)
            self.content_area.setMaximumHeight(0)
            self.animation.setStartValue(0)
            self.animation.setEndValue(self.content_area.sizeHint().height())
        else:
            self.animation.setStartValue(self.content_area.height())
            self.animation.setEndValue(0)

        self.animation.finished.connect(self._on_animation_done)
        self.animation.start()

    def _on_animation_done(self):
        if not self.toggle_button.isChecked():
            self.content_area.setVisible(False)

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
        self.content_area.setMaximumHeight(self.content_area.sizeHint().height())


# === Demo Application ===
class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Read-only Collapsible GroupBox Demo")

        group = CollapsibleGroupBox("Cell Settings")
        group.addWidget(self._parameter_row("Frame Structure", "TDD"))
        group.addWidget(self._parameter_row("Frequency Range", "FR1"))
        group.addWidget(self._parameter_row("UL Spacing", "30kHz"))
        group.addWidget(self._parameter_row("Channel BW", "100MHz"))
        group.addWidget(self._parameter_row("DL/UL Periodicity", "10ms"))
        group.addWidget(self._parameter_row("UL Duration", "10"))

        main_layout = QVBoxLayout()
        main_layout.addWidget(group)
        main_layout.addStretch()
        self.setLayout(main_layout)
        self.resize(320, 300)

    def _parameter_row(self, label_text, value_text):
        row = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(label_text)
        label.setStyleSheet("QLabel { color: black; }")

        value = QLabel(value_text)
        value.setFixedWidth(120)  # or whatever consistent width you want
        value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        value.setStyleSheet("""
            QLabel {
                background-color: white;
                color: black;
                padding: 2px 4px;
                border: 1px solid #888;
                border-radius: 3px;
            }
        """)


        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(value)
        layout.setStretch(1, 1)

        row.setLayout(layout)
        return row


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec())
