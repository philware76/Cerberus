import logging
from typing import Dict, List, Type
from PySide6.QtWidgets import QWidget

from plugins.baseParameters import BaseParameters
from plugins.equipment.baseEquipment import BaseEquipment

from .baseTestResult import BaseTestResult
from plugins.basePlugin import BasePlugin


class BaseTest(BasePlugin):
    def __init__(self, name):
        super().__init__(name)
        self.result = None
        self.widget = None
        self.RequiredEquipment: List[Type[BaseEquipment]] = []
        self.Parameters: Dict[str, BaseParameters] = {}

    def Initialise(self) -> bool:
        logging.debug(f"Initialising")
        return True

    # Do not use this if we are running headless/CLI/test runner etc!
    def getUI(self) -> QWidget:
        self.widget = QWidget()
        self.widget.setWindowTitle(self.name)
        return self.widget

    def _addRequirements(self, typeNames):
        self.RequiredEquipment.extend(typeNames)

    def run(self):
        logging.info(f"Running test: {self.name}")

    def stop(self):
        logging.info(f"Stopping test: {self.name}")

    def getResult(self) -> BaseTestResult:
        return self.result
