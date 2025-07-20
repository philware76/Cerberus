import logging
from plugins.basePlugin import BasePlugin

class BaseEquipment(BasePlugin):
    def __init__(self, name):
        super().__init__(name)
        self.initialised = False

    def Initialise(self) -> bool:
        logging.debug(f"Initialising")
        self.initialised = True
        return True

    def isInitialised(self) -> bool:
        return self.initialised