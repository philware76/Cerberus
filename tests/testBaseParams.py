import pytest
from plugins.baseParameters import BaseParameter


def test_baseparameter_to_dict():
    param = BaseParameter(name="Voltage", value=3.3)
    expected = {"name": "Voltage", "value": 3.3}
    assert param.to_dict() == expected


def test_baseparameter_from_dict():
    d = {"name": "Current", "value": 1.5}
    param = BaseParameter.from_dict(d)
    assert isinstance(param, BaseParameter)
    assert param.name == "Current"
    assert param.value == 1.5
