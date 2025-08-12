import logging
from typing import Any

from Cerberus.plugins.basePlugin import BasePlugin


class BaseProduct(BasePlugin):
    def __init__(self, name: str, description: str | None = None):
        super().__init__(name, description)

    def initialise(self, init: Any = None) -> bool:
        logging.debug("Initialise")
        return True

    def configure(self, config: Any = None) -> bool:
        logging.debug("Configure")
        return True

    def finalise(self) -> bool:
        logging.debug("Finalise")
        return True
