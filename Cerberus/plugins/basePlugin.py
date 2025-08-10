import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import pluggy

from Cerberus.plugins.baseParameters import BaseParameters

hookimpl = pluggy.HookimplMarker("cerberus")
hookspec = pluggy.HookspecMarker("cerberus")


def singleton(cls):
    _instances = {}

    def get_instance(*args, **kwargs):
        if cls not in _instances:
            _instances[cls] = cls(*args, **kwargs)

        return _instances[cls]

    return get_instance


class BasePlugin(ABC):
    def __init__(self, name: str, description: Optional[str] = None):
        self.name = name
        self.description = description
        self._initialised = False
        self.configured = False
        self.finalised = False

        self._init: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}

        self._groupParams: Dict[str, BaseParameters] = {}

        logging.debug(f"__init__ {name}")

    def addParameterGroup(self, group: BaseParameters):
        if group.groupName in self._groupParams:
            logging.warning(f"Parameter group '{group.groupName}' already exists. Overwriting.")

        self._groupParams[group.groupName] = group

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
