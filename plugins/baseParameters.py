from typing import Any, Dict


class BaseParameter():
    def __init__(self, name: str, default: Any, units: str, minValue=float | None, maxValue=float | None, description: (str | None) = None) -> None:
        self.name = name
        self.default = default
        self.units = units
        self.minValue = minValue
        self.maxValue = maxValue
        self.description = description


class BaseParameters(Dict[str, BaseParameter]):
    def __init__(self, groupName: str):
        self.groupName = groupName

    def addParameter(self, param: BaseParameter):
        self[param.name] = param
