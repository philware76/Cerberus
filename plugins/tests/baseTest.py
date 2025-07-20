from PySide6.QtWidgets import QWidget

from .baseTestResult import BaseTestResult
from plugins.basePlugin import BasePlugin

class BaseTest(BasePlugin):
    def __init__(self, name):
        super().__init__(name)
        self.result: BaseTestResult = None
        self.widget: QWidget = None
        self.RequiredEquipment = []

    def Initialise(self) -> bool:
        print(f"Initialising test: {self.name}")
        self.widget = QWidget()
        self.widget.setWindowTitle(self.name)
        return True

    def getWidget(self) -> QWidget:
        return self.widget

    def run(self):
        print(f"Running test: {self.name}")

    def stop(self):
        print(f"Stopping test: {self.name}")

    def getResult(self) -> BaseTestResult:
        return self.result