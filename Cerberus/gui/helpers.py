from typing import Dict

from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

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


def displayParametersUI(pluginName: str, groups: Dict[str, BaseParameters]):
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

    apply_btn.clicked.connect(on_apply)

    window.setWindowTitle(f"{pluginName} Parameters")
    window.resize(400, 300)
    window.show()

    qapp.exec()
