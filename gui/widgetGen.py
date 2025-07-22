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
        spin.setSingleStep(0.1)
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
