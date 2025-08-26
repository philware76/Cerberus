import logging
from typing import Any, Type, cast

import pytest

from Cerberus.plugins.baseParameters import (BaseParameter, BaseParameters,
                                             EnumParameter, NumericParameter,
                                             OptionParameter, StringParameter)

testCaseParameters: dict[str, tuple[dict[str, Any], str]] = {
    "NumericParameter": (
        {
            "name": "Voltage",
            "value": 3.3,
            "units": "V",
            "minValue": 6,
            "maxValue": 24,
            "description": "Voltage"
        },
        "numeric"
    ),
    "OptionParameter": (
        {
            "name": "EnableFeature",
            "value": True,
            "description": "Enable or disable the feature"
        },
        "option"
    ),
    "StringParameter": (
        {
            "name": "DeviceID",
            "value": "ABC123",
            "description": "Identifier for the device"
        },
        "string"
    ),
    "EnumParameter": (
        {
            "name": "Mode",
            "value": "Auto",
            "enumType": ["Auto", "Manual", "Off"],
            "description": "Operating mode"
        },
        "enum"
    ),
}


def get_parameter_subclasses():
    return BaseParameter.__subclasses__()


@pytest.mark.parametrize("ParameterClass", get_parameter_subclasses())
def test_IndividualParameters(ParameterClass, warn_assert):
    class_name = ParameterClass.__name__

    if class_name not in testCaseParameters:
        warnMsg = f"No test data for {class_name}"
        warn_assert(False, warnMsg)
        pytest.skip(warnMsg)

    param_input, expected_type = testCaseParameters[class_name]
    param = ParameterClass(**param_input)

    # to_dict
    param_dict = param.to_dict()
    for key, expected_value in param_input.items():
        actual_value = param_dict.get(key)
        logging.debug(f"Checking {key}: {expected_value} == {actual_value}")
        assert actual_value == expected_value, f"Mismatch for key '{key}': expected {expected_value!r}, got {actual_value!r}"

    assert param_dict["type"] == expected_type

    # __repr__ + eval + __str__
    recreated = eval(repr(param))
    assert isinstance(recreated, ParameterClass)
    assert str(recreated) == str(param.value)

    # from_dict
    param2 = ParameterClass.from_dict(param_dict)
    assert param2 == param


CLASS_NAME_MAP = {
    "NumericParameter": NumericParameter,
    "OptionParameter": OptionParameter,
    "EnumParameter": EnumParameter,
    "StringParameter": StringParameter
}


def test_BaseParameters():
    group_name = "TestGroup"
    params = BaseParameters(group_name)

    # Create BaseParameters from the string-keyed test cases
    for class_name, value in testCaseParameters.items():
        data_raw,  _ = value
        data: dict[str, Any] = data_raw

        ParamClass = cast(Type[BaseParameter], CLASS_NAME_MAP[class_name])
        param = ParamClass(**data)

        params.addParameter(param)

    # Serialize to dict
    param_dict = params.to_dict()

    assert param_dict["groupName"] == group_name
    assert "parameters" in param_dict
    assert isinstance(param_dict["parameters"], dict)
    assert len(param_dict["parameters"]) == len(testCaseParameters)

    # Deserialize
    reconstructed = BaseParameters.from_dict(group_name, param_dict["parameters"])
    assert reconstructed.groupName == group_name
    assert len(reconstructed) == len(params)

    # Compare each parameter
    for name, original_param in params.items():
        recreated_param = reconstructed[name]
        assert isinstance(recreated_param, original_param.__class__)
        assert recreated_param == original_param


def test_baseparameters_unknown_type_raises():
    group_name = "BadGroup"
    bad_param_dict = {
        "UnknownParam": {
            "name": "Something",
            "value": 123,
            "type": "nonexistent_type"
        }
    }

    with pytest.raises(ValueError, match=r"Unknown parameter type: nonexistent_type"):
        BaseParameters.from_dict(group_name, bad_param_dict)


def test_eq_identical_objects():
    p1 = NumericParameter(name="V", value=1.2, units="V")
    p2 = NumericParameter(name="V", value=1.2, units="V")
    assert p1 == p2


def test_eq_different_type():
    p = NumericParameter(name="V", value=1.2, units="V")
    assert (p == "not_a_parameter") is False  # NotImplemented triggers fallback to False


def test_eq_missing_key_in_other():
    class CustomParam(NumericParameter):
        def to_dict(self):
            d = super().to_dict()
            d.pop("units")  # Remove a key from comparison
            return d

    p1 = NumericParameter(name="V", value=1.2, units="V")
    p2 = CustomParam(name="V", value=1.2, units="V")
    assert p1 != p2


def test_eq_extra_key_in_other():
    class CustomParam(NumericParameter):
        def to_dict(self):
            d = super().to_dict()
            d["extra"] = 123  # Add extra key
            return d

    p1 = NumericParameter(name="V", value=1.2, units="V")
    p2 = CustomParam(name="V", value=1.2, units="V")
    assert p1 != p2


def test_eq_mismatched_value():
    p1 = NumericParameter(name="V", value=1.2, units="V")
    p2 = NumericParameter(name="V", value=2.5, units="V")
    assert p1 != p2
    p2 = NumericParameter(name="V", value=2.5, units="V")
    assert p1 != p2


def test_widget_dependency_methods():
    """Test the widget dependency methods on BaseParameter."""
    # Create parameters
    control_param = OptionParameter("Control", False)
    dependent_param = NumericParameter("Dependent", 10)

    # Test initial state
    assert not dependent_param.hasWidgetDependencies()
    assert len(dependent_param.getWidgetDependencies()) == 0

    # Set dependency
    dependent_param.setWidgetDependency("enabled", control_param)

    # Test dependency is set
    assert dependent_param.hasWidgetDependencies()
    deps = dependent_param.getWidgetDependencies()
    assert "enabled" in deps
    assert deps["enabled"] is control_param


def test_widget_dependency_multiple():
    """Test setting multiple widget dependencies on a single parameter."""
    control1 = OptionParameter("Control1", False)
    control2 = OptionParameter("Control2", True)
    dependent = NumericParameter("Dependent", 5)

    # Set multiple dependencies
    dependent.setWidgetDependency("enabled", control1)
    dependent.setWidgetDependency("visible", control2)

    # Verify both dependencies
    assert dependent.hasWidgetDependencies()
    deps = dependent.getWidgetDependencies()
    assert len(deps) == 2
    assert deps["enabled"] is control1
    assert deps["visible"] is control2


def test_addParameter_returns_self():
    """Test that addParameter returns self for method chaining."""
    params = BaseParameters("Test")
    param = NumericParameter("Test Param", 42)

    # Test that addParameter returns self (the BaseParameters instance)
    returned_params = params.addParameter(param)
    assert returned_params is params
    assert params["Test Param"] is param

    # Test that we can chain addParameter calls
    param2 = NumericParameter("Test Param 2", 24)
    result = params.addParameter(param2).addParameter(NumericParameter("Test Param 3", 36))
    assert result is params
    assert len(params) == 3
    assert "Test Param 2" in params
    assert "Test Param 3" in params


def test_widget_dependency_immutable_copy():
    """Test that getWidgetDependencies returns a copy, not the original dict."""
    control = OptionParameter("Control", False)
    dependent = NumericParameter("Dependent", 10)

    dependent.setWidgetDependency("enabled", control)

    # Get dependencies and modify the returned dict
    deps = dependent.getWidgetDependencies()
    original_length = len(deps)
    deps["test"] = control  # This should not affect the original

    # Verify original is unchanged
    assert len(dependent.getWidgetDependencies()) == original_length
    assert "test" not in dependent.getWidgetDependencies()
