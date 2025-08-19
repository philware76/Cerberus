import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import pluggy

from Cerberus.plugins.baseParameters import BaseParameter, BaseParameters

hookimpl = pluggy.HookimplMarker("cerberus")
hookspec = pluggy.HookspecMarker("cerberus")

# Classic singleton decorator kept for plugin factory functions
_def_singletons: dict[type, Any] = {}


def singleton(cls):
    def get_instance(*args, **kwargs):
        if cls not in _def_singletons:
            _def_singletons[cls] = cls(*args, **kwargs)
        return _def_singletons[cls]

    return get_instance


class BasePlugin(ABC):
    def __init__(self, name: str, description: Optional[str] = None):
        self.name = name
        self.description = description
        self.configured = False
        self.finalised = False

        self._init: dict[str, Any] = {}
        self.config: dict[str, Any] = {}

        self._groupParams: dict[str, BaseParameters] = {}

    def addParameterGroup(self, group: BaseParameters):
        if group.groupName in self._groupParams:
            logging.warning(f"Parameter group '{group.groupName}' already exists. Overwriting.")

        self._groupParams[group.groupName] = group

# --- Parameter Helpers -----------------------------------------------------------------------------------------
    def getGroupParameters(self, groupName: str) -> BaseParameters:
        groupParams = self._groupParams.get(groupName)
        if groupParams is None:
            raise ValueError(f"Plugin: {self.name}, unknown parameter group: {groupName}")

        return groupParams

    def getParameter(self, groupName: str, paramName: str) -> BaseParameter:
        groupParams = self.getGroupParameters(groupName)
        param = groupParams.get(paramName)
        if param is None:
            raise ValueError(f"Plugin: {self.name}.{groupParams.groupName}, unknown parameter: {paramName}")

        return param

    def getParameterValue(self, groupName: str, paramName: str) -> Any:
        param = self.getParameter(groupName, paramName)
        return param.value

    def setParameterValue(self, group: str, paramName: str, value: Any):
        param = self.getParameter(group, paramName)
        param.value = value

    def updateParameters(self, group: str, values: dict[str, Any]):
        for k, v in values.items():
            self.setParameterValue(group, k, v)

    @abstractmethod
    def initialise(self, init: Any = None) -> bool:
        '''Initialises a plugin with some initialisation meta data'''

    @abstractmethod
    def configure(self, config: Any = None) -> bool:
        '''Provides the configuration for the plugin'''

    @abstractmethod
    def finalise(self) -> bool:
        '''finalises a plugin'''
