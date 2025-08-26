"""Tests for widget dependency functionality in widgetGen."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QCheckBox, QSpinBox

from Cerberus.gui.widgetGen import (create_checkbox_dependency,
                                    create_parameters_groupbox,
                                    create_txlevel_test_dependencies)
from Cerberus.plugins.baseParameters import (BaseParameters, NumericParameter,
                                             OptionParameter)


def test_checkbox_dependency_creation():
    """Test that checkbox dependency functions work correctly."""
    # Test default behavior (True enables)
    dep_func = create_checkbox_dependency()
    assert dep_func(True) == True
    assert dep_func(False) == False

    # Test custom behavior (False enables)
    dep_func_false = create_checkbox_dependency(False)
    assert dep_func_false(True) == False
    assert dep_func_false(False) == True


def test_txlevel_dependencies_structure():
    """Test that TxLevelTest dependencies are correctly structured."""
    deps = create_txlevel_test_dependencies()

    assert "Test Specs" in deps
    assert "MHz step" in deps["Test Specs"]
    assert "Full band sweep" in deps["Test Specs"]["MHz step"]

    # Test the validation function
    validation_func = deps["Test Specs"]["MHz step"]["Full band sweep"]
    assert validation_func(True) == True
    assert validation_func(False) == False


def test_parameter_group_with_dependencies(qtbot):
    """Test creating a parameter group with dependencies."""
    # Create test parameters
    class TestParams(BaseParameters):
        def __init__(self):
            super().__init__("Test Group")
            self.addParameter(OptionParameter("Enable Feature", False, description="Enable the feature"))
            self.addParameter(NumericParameter("Feature Value", 10, units="units", minValue=1, maxValue=100,
                                               description="Value when feature is enabled"))

    params = TestParams()

    # Create dependencies
    dependencies = {
        "Feature Value": {
            "Enable Feature": create_checkbox_dependency(True)
        }
    }

    # Create the group box
    groupbox, widget_map = create_parameters_groupbox("Test Group", params, dependencies)

    # Verify widgets were created
    assert "Enable Feature" in widget_map
    assert "Feature Value" in widget_map

    enable_widget = widget_map["Enable Feature"]
    value_widget = widget_map["Feature Value"]

    assert isinstance(enable_widget, QCheckBox)
    assert isinstance(value_widget, QSpinBox)

    # Test initial state - checkbox unchecked, value widget should be disabled
    assert not enable_widget.isChecked()
    assert not value_widget.isEnabled()

    # Test enabling - check the checkbox, value widget should become enabled
    enable_widget.setChecked(True)
    # Process Qt events to trigger signal handling
    qtbot.wait(10)  # Small delay to ensure signal processing
    assert value_widget.isEnabled()

    # Test disabling - uncheck the checkbox, value widget should become disabled
    enable_widget.setChecked(False)
    qtbot.wait(10)  # Small delay to ensure signal processing
    assert not value_widget.isEnabled()


def test_no_dependencies(qtbot):
    """Test that parameter groups work normally without dependencies."""
    class SimpleParams(BaseParameters):
        def __init__(self):
            super().__init__("Simple Group")
            self.addParameter(OptionParameter("Simple Option", True))
            self.addParameter(NumericParameter("Simple Value", 5))

    params = SimpleParams()

    # Create group without dependencies
    groupbox, widget_map = create_parameters_groupbox("Simple Group", params)

    # Verify all widgets are enabled by default
    assert len(widget_map) == 2
    for widget in widget_map.values():
        assert widget.isEnabled()


def test_parameter_based_dependencies(qtbot):
    """Test the new parameter-based dependency system."""
    class TestParams(BaseParameters):
        def __init__(self):
            super().__init__("Test Group")

            # Create parameters
            enable_param = OptionParameter("Enable Feature", False)
            dependent_param = NumericParameter("Feature Value", 10, units="units")

            # Add parameters to group
            self.addParameter(enable_param)
            self.addParameter(dependent_param)

            # Set up dependency using the new parameter-based approach
            dependent_param.setWidgetDependency("enabled", enable_param)

    params = TestParams()

    # Create the group box - no external dependencies needed
    groupbox, widget_map = create_parameters_groupbox("Test Group", params)    # Verify widgets were created
    assert "Enable Feature" in widget_map
    assert "Feature Value" in widget_map

    enable_widget = widget_map["Enable Feature"]
    feature_widget = widget_map["Feature Value"]

    assert isinstance(enable_widget, QCheckBox)
    assert isinstance(feature_widget, QSpinBox)

    # Test initial state - checkbox unchecked, dependent widget should be disabled
    assert not enable_widget.isChecked()
    assert not feature_widget.isEnabled()

    # Test enabling - check the checkbox, dependent widget should become enabled
    enable_widget.setChecked(True)
    qtbot.wait(10)  # Small delay to ensure signal processing
    assert feature_widget.isEnabled()

    # Test disabling - uncheck the checkbox, dependent widget should become disabled
    enable_widget.setChecked(False)
    qtbot.wait(10)  # Small delay to ensure signal processing
    assert not feature_widget.isEnabled()


def test_multiple_widget_dependencies(qtbot):
    """Test that a parameter can have multiple widget dependencies."""
    class TestParams(BaseParameters):
        def __init__(self):
            super().__init__("Test")

            # Create parameters
            control1 = OptionParameter("Control 1", False)
            control2 = OptionParameter("Control 2", True)
            dependent = NumericParameter("Dependent", 5)

            # Add parameters to the group
            self.addParameter(control1)
            self.addParameter(control2)
            self.addParameter(dependent)

            # Set multiple dependencies
            dependent.setWidgetDependency("enabled", control1)
            dependent.setWidgetDependency("visible", control2)

    params = TestParams()

    # Verify the dependencies were set correctly at the parameter level
    dependent_param = params["Dependent"]

    assert dependent_param.hasWidgetDependencies()
    deps = dependent_param.getWidgetDependencies()
    assert len(deps) == 2
    assert "enabled" in deps
    assert "visible" in deps
    assert deps["enabled"] is params["Control 1"]
    assert deps["visible"] is params["Control 2"]


def test_txlevel_style_parameter_usage():
    """Test the TxLevelTest style of parameter definition with dependencies."""
    class TestSpecParams(BaseParameters):
        def __init__(self):
            super().__init__("Test Specs")

            # Create parameters
            fullBandSweepOption = OptionParameter("Full band sweep", False)
            stepValue = NumericParameter("MHz step", 100, units="MHz")

            # Add parameters to group
            self.addParameter(fullBandSweepOption)
            self.addParameter(stepValue)

            # Set dependency
            stepValue.setWidgetDependency("enabled", fullBandSweepOption)

    params = TestSpecParams()

    # Verify the dependency was set correctly
    step_param = params["MHz step"]
    sweep_param = params["Full band sweep"]

    assert step_param.hasWidgetDependencies()
    deps = step_param.getWidgetDependencies()
    assert "enabled" in deps
    assert deps["enabled"] is sweep_param
