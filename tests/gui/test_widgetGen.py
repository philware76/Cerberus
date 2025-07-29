from enum import Enum
from dataclasses import dataclass

# test_parameter_widgets.py
import pytest
from PySide6.QtWidgets import QDoubleSpinBox, QCheckBox, QComboBox, QLineEdit

from Cerberus.gui.widgetGen import create_parameter_widget
from Cerberus.plugins.baseParameters import EnumParameter, NumericParameter, OptionParameter, StringParameter

class Mode(Enum):
    AUTO = 0
    MANUAL = 1

# Use qtbot so you don't have to create a QApplication() !

def test_numeric_widget(qtbot):
    param = NumericParameter(name="voltage", value=3.3, minValue=0, maxValue=5, units="V", description="Voltage level")
    widget = create_parameter_widget(param)

    assert isinstance(widget, QDoubleSpinBox)
    assert widget.value() == 3.3
    assert widget.minimum() == 0
    assert widget.maximum() == 5
    assert widget.suffix().strip() == "V"
    assert widget.toolTip() == "Voltage level"

def test_option_widget(qtbot):
    param = OptionParameter(name="enabled", value=True, description="Enable feature")
    widget = create_parameter_widget(param)

    assert isinstance(widget, QCheckBox)
    assert widget.isChecked()
    assert widget.toolTip() == "Enable feature"

def test_enum_widget(qtbot):
    param = EnumParameter(name="mode", value=Mode.MANUAL, enumType=Mode, description="Select mode")
    widget = create_parameter_widget(param)

    assert isinstance(widget, QComboBox)
    assert widget.count() == len(Mode)
    assert widget.currentText() == "MANUAL"
    assert widget.toolTip() == "Select mode"

def test_string_widget(qtbot):
    param = StringParameter(name="label", value="Test", description="Enter label")
    widget = create_parameter_widget(param)

    assert isinstance(widget, QLineEdit)
    assert widget.text() == "Test"
    assert widget.toolTip() == "Enter label"
