import logging
from plugins.basePlugin import BasePlugin


class BaseProduct(BasePlugin):
    def __init__(self, name):
        super().__init__(name)

    def initialise(self, init) -> bool:
        logging.debug("Initialise")
        self.initialised = True
        return True

    def configure(self, config) -> bool:
        logging.debug("Configure")
        self.configured = True
        return True

    def finalise(self) -> bool:
        logging.debug("Finalise")
        self.finalised = True
        return True
