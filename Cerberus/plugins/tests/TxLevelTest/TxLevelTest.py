import time
import logging

from plugins.baseParameters import BaseParameters, NumericParameter, OptionParameter
from plugins.basePlugin import hookimpl, singleton
from plugins.equipment.chambers.baseChamber import BaseChamber
from plugins.tests.baseTest import BaseTest
from plugins.tests.baseTestResult import BaseTestResult, ResultStatus


@hookimpl
@singleton
def createTestPlugin():
    return TxLevelTest()


class TxLevelTestResult(BaseTestResult):
    def __init__(self, name, status):
        super().__init__(name, status)


class TxLevelTestParameters(BaseParameters):
    def __init__(self, ):
        super().__init__("RF Parameters")

        self.addParameter(NumericParameter("Tx Level", 0.0, units="dBm", minValue=-30, maxValue=+23, description="Sets the Transmit power level"))
        self.addParameter(NumericParameter("Start", -10.5, units="dBm", minValue=0, maxValue=25, description="Sets the Transmit power level"))
        self.addParameter(OptionParameter("Enable Tx PA", True))


class TxLevelTest(BaseTest):
    def __init__(self):
        super().__init__("Tx Level")
        self._addRequirements([BaseChamber])

        self.addParameterGroup(TxLevelTestParameters())

    def run(self):
        super().run()

        for i in range(20):
            logging.info(f"Running TxLevelTest iteration {i + 1}")
            time.sleep(.2)

        self.result = TxLevelTestResult(self.name, ResultStatus.PASSED)
