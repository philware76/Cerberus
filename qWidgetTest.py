from enum import Enum
import logging
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QDoubleSpinBox, QCheckBox, QApplication
)
from PySide6.QtCore import Qt
from typing import Dict, Union, cast

from plugins.baseParameters import BaseParameter, BaseParameters, EmptyParameter, EnumParameter, NumericParameter, OptionParameter, StringParameter


def create_parameter_widget(param: BaseParameter) -> QWidget:
    """Return a QWidget (e.g., QLineEdit or QDoubleSpinBox) for a given parameter."""
    widget = None
    if isinstance(param, NumericParameter):
        spin = QDoubleSpinBox()
        if param.minValue is not None:
            spin.setMinimum(param.minValue)
        if param.maxValue is not None:
            spin.setMaximum(param.maxValue)
        spin.setValue(param.value)
        spin.setSuffix(f" {param.units}" if param.units else "")
        spin.setDecimals(4)
        widget = spin

    elif isinstance(param, OptionParameter):
        checkbox = QCheckBox()
        checkbox.setChecked(bool(param.value))
        widget = checkbox

    elif isinstance(param, EnumParameter):
        combobox = QComboBox()
        enum_members = list(param.enum_type)

        for member in enum_members:
            combobox.addItem(member.name, member)

        combobox.setCurrentIndex(enum_members.index(param.value))
        widget = combobox

    elif isinstance(param, StringParameter):
        text = QLineEdit()
        text.setText(param.value)
        widget = text

    if widget == None:
        logging.error(f"Failed to create widget for {param} parameter")
        emptyLabel = QLabel()
        emptyLabel.setText(f"Unknown Parameter Type: {param.name}")
        return emptyLabel

    if param.description:
        widget.setToolTip(param.description)

    return widget


def create_parameters_groupbox(group_name: str, parameters: Dict[str, BaseParameter]) -> tuple[QGroupBox, dict[str, QWidget]]:
    groupbox = QGroupBox(group_name)
    vbox = QVBoxLayout()
    widget_map = {}

    for param in parameters.values():
        hbox = QHBoxLayout()
        label = QLabel(f"{param.name}:")
        label.setFixedWidth(120)

        input_widget = create_parameter_widget(param)
        widget_map[param.name] = input_widget

        if isinstance(param, OptionParameter):
            # Label goes inline with checkbox
            hbox.addWidget(input_widget)
            hbox.addWidget(QLabel(param.name))
        else:
            hbox.addWidget(label)
            hbox.addWidget(input_widget)

        vbox.addLayout(hbox)

    groupbox.setLayout(vbox)
    return groupbox, widget_map


def create_all_parameters_ui(groups: Dict[str, BaseParameters]) -> tuple[QWidget, dict[str, dict[str, QWidget]]]:
    container = QWidget()
    main_layout = QVBoxLayout()
    all_widget_map = {}

    for group_name, base_params in groups.items():
        groupbox, widget_map = create_parameters_groupbox(group_name, base_params)
        all_widget_map[group_name] = widget_map
        main_layout.addWidget(groupbox)

    main_layout.addStretch()
    container.setLayout(main_layout)
    return container, all_widget_map


def apply_parameters(groups: Dict[str, BaseParameters], widget_map: dict[str, dict[str, QWidget]]):
    """
    Update BaseParameters with the current values from the widgets.
    """
    for group_name, param_widgets in widget_map.items():
        base_params = groups[group_name]
        for param_name, widget in param_widgets.items():
            param = base_params[param_name]
            if isinstance(widget, QDoubleSpinBox):
                param.value = widget.value()
            elif isinstance(widget, QLineEdit):
                param.value = widget.text()
            elif isinstance(widget, QCheckBox):
                param.value = widget.isChecked()
            elif isinstance(widget, QComboBox):
                param.value = cast(QComboBox, widget).currentData()


class TimingMode(Enum):
    Plaid = 0
    Fast = 1
    Slow = 2


def show_parameters_ui_with_apply():
    import sys
    from PySide6.QtWidgets import QVBoxLayout, QMainWindow

    app = QApplication(sys.argv)

    # Sample data
    bp1 = BaseParameters("Voltage Parameters")
    bp1.addParameter(NumericParameter(name="VCC", value=3.3, units="V", minValue=3.0, maxValue=3.6))
    bp1.addParameter(NumericParameter(name="VDDIO", value=1.8, units="V", minValue=1.6, maxValue=2.0))
    bp1.addParameter(NumericParameter(name="Dangle berries", value=5000, units="Ber", minValue=1000, maxValue=10000))
    bp1.addParameter(StringParameter(name="Username", value="bert.russell", description="It's a coverup!"))
    bp1.addParameter(EmptyParameter())

    bp2 = BaseParameters("Timing Parameters")
    bp2.addParameter(NumericParameter(name="Delay", value=10.0, units="ms"))
    bp2.addParameter(OptionParameter(name="Bert Mode", value=True, description="This is to enable BERT MODE!"))
    bp2.addParameter(EnumParameter("Timing Mode", TimingMode.Fast, enum_type=TimingMode))
    groups = {bp1.groupName: bp1, bp2.groupName: bp2}

    # Main window
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

    window.setWindowTitle("Test Parameters")
    window.resize(400, 300)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    show_parameters_ui_with_apply()
