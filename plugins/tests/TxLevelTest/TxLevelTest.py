from plugins import hookimpl, singleton
from plugins.equipment.chambers.baseChamber import BaseChamber
from plugins.tests.baseTestResult import BaseTestResult, ResultStatus
from plugins.tests.baseTest import BaseTest

@hookimpl
@singleton
def createTestPlugin():
    return TxLevelTest()

class TxLevelTestResult(BaseTestResult):
    def __init__(self, name, status):
        super().__init__(name, status)
 
class TxLevelTest(BaseTest):
    def __init__(self):
        super().__init__("TxLevelTest")
        self._addRequirements([BaseChamber])

    def run(self):
        print(f"Running TxLevelTest: {self.name}")
        
        self.result = TxLevelTestResult(self.name, ResultStatus.PASSED)