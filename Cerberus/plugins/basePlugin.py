import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import pluggy

from Cerberus.plugins.baseParameters import BaseParameters

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
        self._initialised = False
        self.configured = False
        self.finalised = False

        self._init: dict[str, Any] = {}
        self.config: dict[str, Any] = {}

        self._groupParams: dict[str, BaseParameters] = {}

        logging.debug(f"__init__ {name}")

    def addParameterGroup(self, group: BaseParameters):
        if group.groupName in self._groupParams:
            logging.warning(f"Parameter group '{group.groupName}' already exists. Overwriting.")

        self._groupParams[group.groupName] = group

# --- Parameter Helpers -----------------------------------------------------------------------------------------
    def getParameterValue(self, group: str, paramName: str) -> Any | None:
        groupObj = self._groupParams.get(group)
        if not groupObj:
            return None
        param = groupObj.get(paramName)
        if not param:
            return None
        return param.value

    def setParameterValue(self, group: str, paramName: str, value: Any) -> bool:
        groupObj = self._groupParams.get(group)
        if not groupObj:
            return False

        param = groupObj.get(paramName)
        if not param:
            return False

        param.value = value
        return True

    def updateParameters(self, group: str, values: dict[str, Any]):
        for k, v in values.items():
            self.setParameterValue(group, k, v)

    def isInitialised(self) -> bool:
        return self._initialised

    @abstractmethod
    def initialise(self, init: Any = None) -> bool:
        '''Initialises a plugin with some initialisation meta data'''

    @abstractmethod
    def configure(self, config: Any = None) -> bool:
        '''Provides the configuration for the plugin'''

    @abstractmethod
    def finalise(self) -> bool:
        '''finalises a plugin'''
