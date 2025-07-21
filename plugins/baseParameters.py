from typing import Any, Dict, Optional


class BaseParameter():
    def __init__(self, name: str, default: Any, units: str, minValue: Optional[float] = None, maxValue: Optional[float] = None, description: Optional[str] = None) -> None:
        self.name = name
        self.default = default
        self.units = units
        self.minValue = minValue
        self.maxValue = maxValue
        self.description = description

    def __str__(self) -> str:
        if self.minValue is not None and self.maxValue is not None:
            if self.default is not None:
                return f"{self.default} {self.units} (Min:{self.minValue} {self.units}, Max:{self.maxValue} {self.units})"
            else:
                return f"Min:{self.minValue} {self.units}, Max{self.maxValue} {self.units}"
        else:
            return f"{self.default} {self.units}"

    def __repr__(self) -> str:
        return str(self)

    def getDescription(self) -> str | None:
        return self.description


class BaseParameters(Dict[str, BaseParameter]):
    def __init__(self, groupName: str):
        self.groupName = groupName

    def addParameter(self, param: BaseParameter):
        self[param.name] = param
