from typing import Type
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional


class BaseParameter(ABC):
    def __init__(self, name: str, value: Any, units: Optional[str] = "", description: Optional[str] = None):
        self.name = name
        self.value = value
        self.units = units
        self.description = description

    def getDescription(self) -> Optional[str]:
        return self.description

    @abstractmethod
    def to_dict(self) -> dict:
        """"Returns a dictionary of the parameters"""

    @classmethod
    def from_dict(cls, data: dict) -> "OptionParameter":
        data.pop("type", None)
        return cls(**data)

    def __repr__(self) -> str:
        return f"{self.name}:{self.value} {self.units}".strip()


class NumericParameter(BaseParameter):
    def __init__(self, name: str, value: float, units: str = "", minValue: Optional[float] = None,
                 maxValue: Optional[float] = None, description: Optional[str] = None):
        super().__init__(name, value, units, description)
        self.minValue = minValue
        self.maxValue = maxValue

    def to_dict(self) -> dict:
        return {
            "type": "numeric",
            "name": self.name,
            "value": self.value,
            "units": self.units,
            "minValue": self.minValue,
            "maxValue": self.maxValue,
            "description": self.description
        }


class OptionParameter(BaseParameter):
    def __init__(self, name: str, value: bool, description: Optional[str] = None):
        super().__init__(name, value, units="", description=description)

    def to_dict(self) -> dict:
        return {
            "type": "option",
            "name": self.name,
            "value": self.value,
            "description": self.description
        }




class EnumParameter(BaseParameter):
    def __init__(self, name: str, value: Enum, enumType: Type[Enum], description: str = ""):
        super().__init__(name=name, value=value, units="", description=description)
        self.enum_type = enumType

    def to_dict(self) -> dict:
        return {
            "type": "enum",
            "name": self.name,
            "value": self.value.name,  # serialize by enum name
            "enumType": self.enumType.__name__,  # just name, or full path if needed
            "description": self.description,
        }


class StringParameter(BaseParameter):
    def __init__(self, name: str, value: str, description: Optional[str] = None):
        super().__init__(name, value, description=description)

    def to_dict(self) -> dict:
        return {
            "type": "text",
            "name": self.name,
            "value": self.value,
            "description": self.description
        }

class EmptyParameter(BaseParameter):
    def __init__(self):
        super().__init__("Empty", 0, description="Placeholder")

    def to_dict(self) -> dict:
        return {
            "type": "empty",
            "name": self.name,
            "value": self.value,
            "description": self.description
        }


PARAMETER_TYPE_MAP = {
    "numeric": NumericParameter,
    "option": OptionParameter,
    "enum": EnumParameter,
    "text": StringParameter
}


class BaseParameters(dict[str, BaseParameter]):
    def __init__(self, groupName: str):
        super().__init__()
        self.groupName = groupName

    def addParameter(self, param: BaseParameter):
        self[param.name] = param

    def to_dict(self) -> dict:
        return {
            "groupName": self.groupName,
            "parameters": {k: v.to_dict() for k, v in self.items()}
        }

    @classmethod
    def from_dict(cls, groupName:str, data: dict) -> "BaseParameters":
        obj = cls(groupName)
        for name, param_data in data.items():
            param_type = param_data.get("type")
            param_cls = PARAMETER_TYPE_MAP.get(param_type)
            if not param_cls:
                raise ValueError(f"Unknown parameter type: {param_type}")
        
            obj.addParameter(param_cls.from_dict(param_data))

        return obj
