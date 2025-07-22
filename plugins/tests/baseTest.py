import logging
from typing import Dict, List, Optional, Type
from PySide6.QtWidgets import QWidget

from plugins.baseParameters import BaseParameters
from plugins.equipment.baseEquipment import BaseEquipment

from .baseTestResult import BaseTestResult
from plugins.basePlugin import BasePlugin


class BaseTest(BasePlugin):
    def __init__(self, name, description: Optional[str] = None):
        super().__init__(name, description)
        self.result = None
        self.widget = None
        self.requiredEquipment: List[Type[BaseEquipment]] = []
        self.parameters: Dict[str, BaseParameters] = {}

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

    # Do not use this if we are running headless/CLI/test runner etc!
    def getUI(self) -> QWidget:
        self.widget = QWidget()
        self.widget.setWindowTitle(self.name)
        return self.widget

    def _addRequirements(self, typeNames):
        self.requiredEquipment.extend(typeNames)

    def run(self):
        logging.info(f"Running test: {self.name}")

    def stop(self):
        logging.info(f"Stopping test: {self.name}")

    def getResult(self) -> BaseTestResult:
        return self.result
