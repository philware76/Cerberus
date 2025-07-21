import logging
from plugins.basePlugin import BasePlugin


class Identity():
    def __init__(self, idString: str):
        parts = idString.split(",")
        if len(parts) == 4:
            self.manufacturer = parts[0]
            self.model = parts[1]
            self.serial = parts[2]
            self.version = parts[3]
        else:
            self.manufacturer = "Unknown"
            self.model = "Unknown"
            self.serial = "Unknown"
            self.version = "Unknown"


class BaseEquipment(BasePlugin):
    def __init__(self, name):
        super().__init__(name)
        self.identity = Identity("")

    def initialise(self) -> bool:
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
