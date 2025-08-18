from typing import Dict

from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from Cerberus.gui.matplotWidget import MatplotWidget
from Cerberus.gui.widgetGen import apply_parameters, create_all_parameters_ui
from Cerberus.plugins.baseParameters import BaseParameters


def displayWidget(widget: QWidget):
    # Make sure QApplication exists; create one if it doesn't
    qapp = QApplication.instance()
    if qapp is None:
        qapp = QApplication([])

    window = QWidget()
    layout = QVBoxLayout(window)

    layout.addWidget(widget)

    window.setWindowTitle("Widget")
    window.resize(400, 300)
    window.show()

    qapp.exec()


def displayParametersUI(pluginName: str, groups: Dict[str, BaseParameters], *, close_on_apply: bool = True):
    """Show a GUI for the parameters to edit"""
    # Make sure QApplication exists; create one if it doesn't
    qapp = QApplication.instance()
    if qapp is None:
        qapp = QApplication([])

    window = QWidget()
    layout = QVBoxLayout(window)

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
            window.close()

    apply_btn.clicked.connect(on_apply)

    window.setWindowTitle(f"{pluginName} Parameters")
    window.resize(400, 300)
    window.show()

    qapp.exec()


def openMatPlotUI(title: str,
                  xlabel: str,
                  ylabel: str,
                  *,
                  xlim: tuple[float, float] | None = None,
                  ylim: tuple[float, float] | None = None,
                  series: list[str] | None = None,
                  window_title: str = "Matplot Window",
                  width: int = 800,
                  height: int = 500) -> tuple[QApplication, QWidget, MatplotWidget]:
    """Create and show a simple window containing a MatplotWidget.

    Returns (qapp, window, matplot). Caller is responsible for starting the event loop
    (qapp.exec()) or processing events manually.
    """
    qapp = QApplication.instance()
    if qapp is None:
        qapp = QApplication([])

    window = QWidget()
    layout = QVBoxLayout(window)

    # Provide defaults if not specified
    if xlim is None:
        xlim = (0, 10)
    if ylim is None:
        ylim = (0, 10)

    matplot = MatplotWidget(
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        xlim=xlim,
        ylim=ylim
    )
    layout.addWidget(matplot)

    # Pre-create any requested series
    if series:
        for s in series:
            if s not in matplot.series_data:
                matplot.add_series(s)

    window.setWindowTitle(window_title)
    window.resize(width, height)
    window.show()

    return qapp, window, matplot  # type: ignore
