import logging
from typing import Any, ClassVar

from Cerberus.plugins.basePlugin import BasePlugin


class BaseProduct(BasePlugin):
    # Default class-level mappings; product implementations should override
    SLOT_DETAILS_DICT: ClassVar[dict[int, str]] = {}
    FILTER_DICT: ClassVar[dict[int, str]] = {}

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
