import logging
from typing import List, Type
from PySide6.QtWidgets import QWidget

from plugins.equipment.baseEquipment import BaseEquipment

from .baseTestResult import BaseTestResult
from plugins.basePlugin import BasePlugin

class BaseTest(BasePlugin):
    def __init__(self, name):
        super().__init__(name)
        self.result: BaseTestResult = None
        self.widget: QWidget = None
        self.RequiredEquipment : List[Type[BaseEquipment]] = []

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

    async def run(self):
        logging.info(f"Running test: {self.name}")

    def stop(self):
        logging.info(f"Stopping test: {self.name}")

    def getResult(self) -> BaseTestResult:
        return self.result