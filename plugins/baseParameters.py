from typing import Any, Dict, Optional
import json


class BaseParameter():
    def __init__(self, name: str, value: Any, units: str, minValue: Optional[float] = None, maxValue: Optional[float] = None, description: Optional[str] = None) -> None:
        self.name = name
        self.value = value
        self.units = units
        self.minValue = minValue
        self.maxValue = maxValue
        self.description = description

    def __str__(self) -> str:
        if self.minValue is not None and self.maxValue is not None:
            if self.value is not None:
                return f"{self.value} {self.units} (Min:{self.minValue} {self.units}, Max:{self.maxValue} {self.units})"

            return f"Min:{self.minValue} {self.units}, Max{self.maxValue} {self.units}"
        else:
            return f"{self.value} {self.units}"

    def __repr__(self) -> str:
        return str(self)

    def getDescription(self) -> str | None:
        return self.description

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "units": self.units,
            "minValue": self.minValue,
            "maxValue": self.maxValue,
            "description": self.description
        }

    @classmethod
    def fromDict(cls, data: dict) -> "BaseParameter":
        return cls(**data)


class BaseParameters(Dict[str, BaseParameter]):
    def __init__(self, groupName: str):
        super().__init__()
        self.groupName = groupName

    def addParameter(self, param: BaseParameter):
        self[param.name] = param

    def toDict(self) -> dict:
        return {
            "groupName": self.groupName,
            "parameters": {k: v.to_dict() for k, v in self.items()}
        }

    @classmethod
    def fromDict(cls, data: dict) -> "BaseParameters":
        obj = cls(groupName=data["groupName"])
        for name, param_data in data["parameters"].items():
            obj[name] = BaseParameter.fromDict(param_data)
        return obj

    def toJson(self):
        return json.dumps(self.toDict())

    @classmethod
    def fromJson(cls, jsonStr):
        return BaseParameters.fromDict(json.loads(jsonStr))
