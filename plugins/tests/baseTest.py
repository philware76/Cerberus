import logging
from typing import List, Optional, Type

from plugins.equipment.baseEquipment import BaseEquipment

from .baseTestResult import BaseTestResult
from plugins.basePlugin import BasePlugin


class BaseTest(BasePlugin):
    def __init__(self, name, description: Optional[str] = None):
        super().__init__(name, description)
        self.result: BaseTestResult | None = None
        self.requiredEquipment: List[Type[BaseEquipment]] = []

    def initialise(self, init=None) -> bool:
        logging.debug("Initialise")
        if init is not None:
            self.init = init

        self.initialised = True
        return True

    def configure(self, config=None) -> bool:
        logging.debug("Configure")
        if config is not None:
            self.config = config

        self.configured = True
        return True

    def finalise(self) -> bool:
        logging.debug("Finalise")
        self.finalised = True
        return True

    def _addRequirements(self, typeNames):
        self.requiredEquipment.extend(typeNames)

    def run(self):
        logging.info(f"Running test: {self.name}")

    def stop(self):
        logging.info(f"Stopping test: {self.name}")

    def getResult(self) -> BaseTestResult | None:
        return self.result
