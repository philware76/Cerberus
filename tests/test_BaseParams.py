import pytest
from plugins.baseParameters import BaseParameter, NumericParameter, OptionParameter

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
    # You can add other test cases here keyed by class name
}


def get_parameter_subclasses():
    return BaseParameter.__subclasses__()


@pytest.mark.parametrize("ParameterClass", get_parameter_subclasses())
def test_parameter_serialization(ParameterClass, warn_assert):
    class_name = ParameterClass.__name__

    if class_name not in parameter_test_cases:
        warn_assert(False, f"No test data for {class_name}")
        pytest.skip(f"No test data for {class_name}")

    param_input, expected_str, expected_type = parameter_test_cases[class_name]
    print(f"\n🔍 Testing {class_name}")

    param = ParameterClass(**param_input)

    # to_dict
    param_dict = param.to_dict()
    for key, expected_value in param_input.items():
        actual_value = param_dict.get(key)
        assert actual_value == expected_value, f"Mismatch for key '{key}': expected {expected_value!r}, got {actual_value!r}"

    assert param_dict["type"] == expected_type

    # __repr__ + eval + __str__
    recreated = eval(repr(param))
    assert isinstance(recreated, ParameterClass)
    assert str(recreated) == expected_str

    # from_dict
    param2 = ParameterClass.from_dict(param_dict)
    assert param2 == param


def test_something(warn_assert):
    warn_assert(2 + 2 == 5, "Math seems wrong but not fatal")


def test_somethingelse():
    assert 5 == 4
