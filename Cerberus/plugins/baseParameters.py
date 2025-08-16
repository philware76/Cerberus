import importlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Self, Type


class GenRepr:
    def __init__(self, instance):
        self.class_name = instance.__class__.__name__
        self.parts = []

    def addParam(self, name, value):
        self.parts.append(f"{name}={repr(value)}")

    def __repr__(self):
        return f"{self.class_name}({', '.join(self.parts)})"


class BaseParameter(ABC):
    def __init__(self, name: str, value: Any, units: Optional[str] = "", description: Optional[str] = None):
        self.name = name
        self.value = value
        self.units = units
        self.description = description
        self.genRepr = GenRepr(self)
        self.genRepr.addParam("name", self.name)
        self.genRepr.addParam("value", self.value)

    @abstractmethod
    def to_dict(self) -> dict:
        """"Returns a dictionary of the parameters"""

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        data.pop("type", None)
        return cls(**data)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self):
        return repr(self.genRepr)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented

        self_dict = self.to_dict()
        other_dict = other.to_dict()

        # Exclude 'type' field if it's virtual and not meaningful for equality
        ignore_keys = {"type"}

        for key, value in self_dict.items():
            if key in ignore_keys:
                continue
            if key not in other_dict:
                return False
            if other_dict[key] != value:
                return False

        # Check for unexpected keys in other_dict
        for key in other_dict:
            if key in ignore_keys:
                continue
            if key not in self_dict:
                return False

        return True

    # Delegate common operations to the underlying value so the parameter
    # instance can often be used interchangeably with its .value.
    def __getattr__(self, name: str):
        """If attribute isn't found on the parameter, delegate to the value."""
        return getattr(self.value, name)

    def __int__(self) -> int:  # pragma: no cover - trivial delegation
        return int(self.value)

    def __float__(self) -> float:  # pragma: no cover - trivial delegation
        return float(self.value)

    def __complex__(self) -> complex:  # pragma: no cover - trivial delegation
        return complex(self.value)

    def __bool__(self) -> bool:  # pragma: no cover - trivial delegation
        return bool(self.value)

    def __len__(self) -> int:  # pragma: no cover - trivial delegation
        return len(self.value)

    def __iter__(self):  # pragma: no cover - trivial delegation
        return iter(self.value)

    def __index__(self) -> int:  # pragma: no cover - trivial delegation for indexing
        # __index__ should return an int for operations like slicing/indexing
        return self.value.__index__()


class NumericParameter(BaseParameter):
    def __init__(self, name: str, value: float | int, units: str = "", minValue: Optional[float | int] = None,
                 maxValue: Optional[float | int] = None, description: Optional[str] = None):
        super().__init__(name, value, units, description)
        self.minValue = minValue
        self.maxValue = maxValue
        self.genRepr.addParam("units", self.units)

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
    def __init__(self, name: str, value: Any, enumType: Any, description: str = ""):
        # value may be an Enum instance or a primitive (legacy behaviour)
        super().__init__(name=name, value=value, units="", description=description)
        # enumType may be either an Enum class or an iterable of allowed choice names
        self.enumType = enumType
        self.genRepr.addParam("enumType", self.enumType)

    def to_dict(self) -> dict:
        # Store only JSON-serializable primitives describing the enum
        d: dict = {
            "type": "enum",
            "name": self.name,
            # description included for compatibility
            "description": self.description,
        }

        # If value is an Enum instance, store module/type info and underlying value
        if isinstance(self.value, Enum):
            d.update({
                "value": self.value.value,
                "enumName": self.value.name,
            })
            # If enumType is a class, store its module/name for reconstruction
            if isinstance(self.enumType, type):
                d["enumType"] = self.enumType.__name__
                d["enumModule"] = self.enumType.__module__
            else:
                # Fallback: store choices list if provided instead of a real Enum class
                try:
                    d["enumType"] = list(self.enumType)
                except Exception:
                    d["enumType"] = []
        else:
            # value is a primitive (string/number) — allow legacy usage where enumType is a list
            d["value"] = self.value
            if isinstance(self.enumType, type):
                d["enumType"] = self.enumType.__name__
                d["enumModule"] = self.enumType.__module__
            else:
                # store the provided choices (if iterable) using legacy 'enumType' key
                try:
                    d["enumType"] = list(self.enumType)
                except Exception:
                    d["enumType"] = []

        return d

    @classmethod
    def from_dict(cls, data: dict) -> "EnumParameter":  # type: ignore[override]
        """Reconstruct an EnumParameter from serialized dict produced by to_dict."""
        enum_module = data.get("enumModule")
        enum_type_name = data.get("enumType")
        raw_value = data.get("value")
        enum_name = data.get("enumName")
        name = data.get("name") or "<unnamed-enum>"
        description = data.get("description") or ""

        # If module and type name are provided, try to reconstruct the real Enum class.
        if enum_module and enum_type_name:
            try:
                mod = importlib.import_module(enum_module)
                enum_cls = getattr(mod, enum_type_name)
            except Exception as ex:  # pragma: no cover
                raise ValueError(f"Failed to import enum {enum_module}.{enum_type_name}: {ex}") from ex
            # Reconstruct true Enum subclass
            if raw_value is not None:
                try:
                    enum_val = enum_cls(raw_value)
                except Exception:
                    try:
                        enum_val = getattr(enum_cls, str(raw_value))
                    except Exception as ex:
                        raise ValueError(f"Cannot reconstruct enum value for {enum_cls} from {raw_value}") from ex
            elif enum_name:
                try:
                    enum_val = getattr(enum_cls, enum_name)
                except Exception as ex:  # pragma: no cover
                    raise ValueError(f"Cannot reconstruct enum by name {enum_name} for {enum_cls}") from ex
            else:
                raise ValueError("EnumParameter.from_dict missing both value and enumName")

            return cls(name=name, value=enum_val, enumType=enum_cls, description=description)

        # Else, handle legacy 'enumChoices' where enumType was a list of names
        # Accept legacy shapes: either 'enumChoices' or a list-valued 'enumType'
        enum_choices = data.get("enumChoices")
        if enum_choices is None:
            maybe_et = data.get("enumType")
            if isinstance(maybe_et, (list, tuple)):
                enum_choices = list(maybe_et)

        if enum_choices is not None:
            # raw_value may be primitive (string) — preserve as-is
            return cls(name=name, value=raw_value, enumType=enum_choices, description=description)

        raise ValueError("EnumParameter.from_dict could not determine enum type information")


class StringParameter(BaseParameter):
    def __init__(self, name: str, value: str, description: Optional[str] = None):
        super().__init__(name, value, description=description)

    def to_dict(self) -> dict:
        return {
            "type": "string",
            "name": self.name,
            "value": self.value,
            "description": self.description
        }


PARAMETER_TYPE_MAP = {
    "numeric": NumericParameter,
    "option": OptionParameter,
    "enum": EnumParameter,
    "string": StringParameter
}


class BaseParameters(dict[str, BaseParameter]):
    def __init__(self, groupName: str):
        super().__init__()
        self.groupName = groupName

    def addParameter(self, param: BaseParameter):
        self[param.name] = param
        return self

    def to_dict(self) -> dict:
        return {
            "groupName": self.groupName,
            "parameters": {k: v.to_dict() for k, v in self.items()}
        }

    @classmethod
    def from_dict(cls, groupName: str, data: dict) -> "BaseParameters":
        obj = cls(groupName)
        for _, param_data in data.items():
            param_type = param_data.get("type")
            param_cls = PARAMETER_TYPE_MAP.get(param_type)
            if not param_cls:
                raise ValueError(f"Unknown parameter type: {param_type}")

            obj.addParameter(param_cls.from_dict(param_data))

        return obj
