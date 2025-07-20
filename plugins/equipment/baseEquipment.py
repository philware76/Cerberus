import logging

class BaseEquipment:
    def __init__(self, name):
        self.name = name
        self.initialised = False

    def Initialise(self) -> bool:
        logging.debug(f"Initialising")
        self.initialised = True
        return True

    def getName(self) -> str:
        return self.name

    def isInitialised(self) -> bool:
        return self.initialised