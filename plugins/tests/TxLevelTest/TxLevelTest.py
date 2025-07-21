import asyncio
import logging

from plugins.basePlugin import hookimpl, singleton
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

    async def run(self):
        await super().run()

        for i in range(20):
            logging.info(f"Running TxLevelTest iteration {i + 1}")
            await asyncio.sleep(1)

        self.result = TxLevelTestResult(self.name, ResultStatus.PASSED)