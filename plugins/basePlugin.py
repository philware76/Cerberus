from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
import pluggy

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
    def __init__(self, name, description: Optional[str] = None):
        self.name = name
        self.description = description
        self.initialised = False
        self.configured = False
        self.finalised = False

        logging.debug(f"__init__ {name}")

    @abstractmethod
    def initialise(self, init: Dict[str, Any]) -> bool:
        '''Intialises a plugin with some initlisation meta data'''

    @abstractmethod
    def configure(self, config) -> bool:
        '''Provides the configuration for the plugin'''

    @abstractmethod
    def finalise(self) -> bool:
        '''finalises a plugin'''
