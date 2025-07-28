from enum import Enum
import time
import logging

from plugins.baseParameters import BaseParameter, BaseParameters, EnumParameter, NumericParameter, OptionParameter, StringParameter
from plugins.basePlugin import hookimpl, singleton
from plugins.equipment.simpleEquip.simpleEquip1 import SimpleEquip1
from plugins.tests.baseTestResult import BaseTestResult, ResultStatus
from plugins.tests.baseTest import BaseTest


@hookimpl
@singleton
def createTestPlugin():
    return SimpleTest1()


class SimpleTestResult(BaseTestResult):
    def __init__(self, name, status):
        super().__init__(name, status)
        logging.trace("Created Simple Test Result")


class SimpleEnum(Enum):
    One = 1
    Two = 2
    Three = 3


class SimpleTestParameters(BaseParameters):
    def __init__(self, ):
        super().__init__("RF Parameters")

        self.addParameter(NumericParameter("Number", 0.0, units="dBm", minValue=-30, maxValue=+23, description="Number parameter"))
        self.addParameter(OptionParameter("Option", True, description="Option parameter"))
        self.addParameter(EnumParameter("Select", SimpleEnum.One, SimpleEnum, "Selection parameter"))
        self.addParameter(StringParameter("Text", "This is text", "Text parameter"))


class SimpleTest1(BaseTest):
    def __init__(self):
        super().__init__("Simple Test #1")
        self._addRequirements([SimpleEquip1])

        self.addParameterGroup(SimpleTestParameters())

    def run(self):
        super().run()

        for i in range(20):
            logging.info(f"Running {self.name} iteration {i + 1}")
            time.sleep(1)

        self.result = SimpleTestResult(self.name, ResultStatus.PASSED)
