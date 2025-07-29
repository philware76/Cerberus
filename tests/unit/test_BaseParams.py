import pytest
import logging
from typing import Any, Type, cast


from plugins.baseParameters import BaseParameters, BaseParameter, NumericParameter, OptionParameter, StringParameter, EnumParameter

testCaseParameters: dict[str, tuple[dict[str, Any], str, str]] = {
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
def test_IndividualParameters(ParameterClass, warn_assert):
    class_name = ParameterClass.__name__

    if class_name not in testCaseParameters:
        warnMsg = f"No test data for {class_name}"
        warn_assert(False, warnMsg)
        pytest.skip(warnMsg)

    param_input, expected_str, expected_type = testCaseParameters[class_name]
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
        data_raw, _, _ = value
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
