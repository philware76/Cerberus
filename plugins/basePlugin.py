import logging
from typing import Optional
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


class BasePlugin:
    def __init__(self, name, description: Optional[str] = None):
        self.name = name
        self.description = description
        logging.debug(f"__init__ {name}")
