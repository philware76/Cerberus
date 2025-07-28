import pytest
from plugins.baseParameters import BaseParameter, NumericParameter, OptionParameter, StringParameter, EnumParameter

import logging
logging.basicConfig(level=logging.INFO)

parameter_test_cases = {
    "NumericParameter": (
        {
            "name": "Voltage",
            "value": 3.3,
            "units": "V",
            "minValue": 6,
            "maxValue": 24,
            "description": "Voltage"
        },
        "Voltage:3.3 V",
        "numeric"
    ),
    "OptionParameter": (
        {
            "name": "EnableFeature",
            "value": True,
            "description": "Enable or disable the feature"
        },
        "EnableFeature:True",
        "option"
    ),
    "StringParameter": (
        {
            "name": "DeviceID",
            "value": "ABC123",
            "description": "Identifier for the device"
        },
        "DeviceID:ABC123",
        "string"
    ),
    "EnumParameter": (
        {
            "name": "Mode",
            "value": "Auto",
            "enumType": ["Auto", "Manual", "Off"],
            "description": "Operating mode"
        },
        "Mode:Auto",
        "enum"
    ),
}


def get_parameter_subclasses():
    return BaseParameter.__subclasses__()


@pytest.mark.parametrize("ParameterClass", get_parameter_subclasses())
def test_parameter_serialization(ParameterClass, warn_assert):
    class_name = ParameterClass.__name__

    if class_name not in parameter_test_cases:
        warnMsg = f"No test data for {class_name}"
        warn_assert(False, warnMsg)
        pytest.skip(warnMsg)

    param_input, expected_str, expected_type = parameter_test_cases[class_name]
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
    assert str(recreated) == expected_str

    # from_dict
    param2 = ParameterClass.from_dict(param_dict)
    assert param2 == param
