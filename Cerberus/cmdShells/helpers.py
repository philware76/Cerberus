import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect,
                               QGroupBox, QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget)


class SplashController:
    """Controller for splash screen dynamic updates."""

    def __init__(self, widget: QWidget, status_label: QLabel):
        self._widget = widget
        self._status_label = status_label

    def update_status(self, text: str):
        self._status_label.setText(text)
        app = QApplication.instance()
        if app:
            app.processEvents()

    def close(self):
        self._widget.close()


def show_image_splash(
    argv: list[str],
    image_path: str = "image1.png",
    line1: str = "SmithMyers 2025",
    line2: str = "v1.0.0b",
    scale: float = 0.5,
    with_status: bool = True,
) -> SplashController | None:
    """Display a borderless window showing an image and two labels top-right.

    Closes when the user clicks anywhere on the window.
    Safe to call if a QApplication already exists; otherwise one is created
    temporarily (and will block until the splash is closed).
    """
    app_created = False
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv)
        app_created = True

    # Resolve image path relative to repository root if needed
    if not os.path.isfile(image_path):
        # Try relative to this file's directory two levels up (repo root assumption)
        candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', image_path))
        if os.path.isfile(candidate):
            image_path = candidate

    original_pixmap = QPixmap(image_path)
    if original_pixmap.isNull():
        raise FileNotFoundError(f"Splash image not found or invalid: {image_path}")

    # Constrain scale
    if scale <= 0:
        scale = 0.5
    if scale > 1.0:
        scale = 1.0

    target_w = max(1, int(original_pixmap.width() * scale))
    target_h = max(1, int(original_pixmap.height() * scale))
    pixmap = original_pixmap.scaled(
        target_w,
        target_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    status_label_holder: dict[str, QLabel] = {}

    class _Splash(QWidget):
        def __init__(self):
            # Use window flags for a frameless tool window
            super().__init__(None, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setWindowTitle("Splash")
            self.pixmap = pixmap
            self.resize(self.pixmap.size())

            # Main image label fills background
            self.image_label = QLabel(self)
            self.image_label.setPixmap(self.pixmap)
            self.image_label.setScaledContents(False)
            self.image_label.resize(self.pixmap.size())

            # Overlay container for text labels (top-right)
            overlay = QWidget(self)
            overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            overlay_layout = QVBoxLayout(overlay)
            overlay_layout.setContentsMargins(0, 0, 0, 0)

            top_row = QHBoxLayout()
            top_row.addStretch(1)  # push labels to right

            label_container = QVBoxLayout()

            def _make_label(text: str) -> QLabel:
                lbl = QLabel(text)
                font = QFont()
                font.setPointSize(12)  # bigger
                font.setBold(True)
                lbl.setFont(font)
                lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                lbl.setStyleSheet("color: white; background: transparent; padding: 2px 6px;")
                lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                # Add shadow (acts like outline)
                shadow = QGraphicsDropShadowEffect(lbl)
                shadow.setOffset(0, 0)
                shadow.setBlurRadius(6)
                shadow.setColor(QColor(0, 0, 0, 200))
                lbl.setGraphicsEffect(shadow)
                return lbl

            label_container.addWidget(_make_label(line1), alignment=Qt.AlignmentFlag.AlignRight)
            label_container.addWidget(_make_label(line2), alignment=Qt.AlignmentFlag.AlignRight)

            top_row.addLayout(label_container)
            top_row.addSpacing(6)
            overlay_layout.addLayout(top_row)
            overlay_layout.addStretch(1)  # push following bottom row to bottom

            # Bottom full-width group box containing status label
            if with_status:
                group = QGroupBox()
                group.setTitle("")
                group.setStyleSheet(
                    "QGroupBox {"
                    "border: 1px solid #666;"
                    "border-radius: 4px;"
                    "margin-top: 0px;"
                    "background-color: rgba(0,0,0,110);"
                    "}"
                )
                g_layout = QHBoxLayout(group)
                g_layout.setContentsMargins(6, 3, 6, 3)
                g_layout.setSpacing(0)
                status = QLabel("")
                f = QFont()
                f.setPointSize(10)
                f.setBold(False)
                status.setFont(f)
                status.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                status.setStyleSheet("color: white; background: transparent; border: none; margin: 0; padding: 0;")
                status.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                status.setWordWrap(True)
                g_layout.addWidget(status)
                overlay_layout.addWidget(group)
                status_label_holder["label"] = status

            overlay.resize(self.pixmap.size())

        def mousePressEvent(self, event):  # noqa: N802
            self.close()

        def closeEvent(self, event):  # noqa: N802
            # If this helper created the QApplication, request its shutdown so app.exec() returns
            if app_created:
                qapp = QApplication.instance()
                if qapp is not None:
                    qapp.quit()

            super().closeEvent(event)

    splash = _Splash()
    # Center on primary screen
    scr = QApplication.primaryScreen()
    if scr:
        geo = scr.availableGeometry()
        x = geo.x() + (geo.width() - splash.width()) // 2
        y = geo.y() + (geo.height() - splash.height()) // 2
        splash.move(x, y)

    splash.show()

    # If we created the app, exec its event loop until splash closed
    # Process initial events
    app.processEvents()
    controller = SplashController(splash, status_label_holder.get("label", QLabel()))
    return controller
