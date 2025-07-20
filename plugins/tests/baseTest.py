import logging
from PySide6.QtWidgets import QWidget

from .baseTestResult import BaseTestResult
from plugins.basePlugin import BasePlugin

class BaseTest(BasePlugin):
    def __init__(self, name):
        super().__init__(name)
        self.result: BaseTestResult = None
        self.widget: QWidget = None
        self.RequiredEquipment = []
        logging.debug(f"__init__ {name}")

    def Initialise(self) -> bool:
        logging.debug(f"Initialising")
        self.widget = QWidget()
        self.widget.setWindowTitle(self.name)
        return True

    def _addRequirements(self, typeNames):
        self.RequiredEquipment.extend(typeNames)

    def getWidget(self) -> QWidget:
        return self.widget

    def run(self):
        logging.info(f"Running test: {self.name}")

    def stop(self):
        logging.info(f"Stopping test: {self.name}")

    def getResult(self) -> BaseTestResult:
        return self.result