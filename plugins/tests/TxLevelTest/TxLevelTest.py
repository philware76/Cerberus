from plugins import hookimpl
from plugins.tests.baseTestResult import BaseTestResult, ResultStatus
from plugins.tests.baseTest import BaseTest

@hookimpl
def createTestPlugin():
    return TxLevelTest()

class TxLevelTestResult(BaseTestResult):
    def __init__(self, name, status):
        super().__init__(name, status)

class TxLevelTest(BaseTest):
    def __init__(self):
        super().__init__("TxLevelTest")
        self.RequiredEquipment.append("BaseChamber")

    def run(self):
        print(f"Running TxLevelTest: {self.name}")
        
        self.result = TxLevelTestResult(self.name, ResultStatus.PASSED)