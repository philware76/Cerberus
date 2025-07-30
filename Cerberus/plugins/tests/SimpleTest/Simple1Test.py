import logging
import time
from enum import Enum

from Cerberus.plugins.baseParameters import (BaseParameters, EnumParameter,
                                             NumericParameter, OptionParameter,
                                             StringParameter)
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.simpleEquip.simple1Equipment import \
    SimpleEquip1
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import BaseTestResult, ResultStatus


@hookimpl
@singleton
def createTestPlugin():
    return SimpleTest1()


class SimpleTestResult(BaseTestResult):
    def __init__(self, name, status):
        super().__init__(name, status)
        logging.debug("Created Simple Test Result")


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

        count = self.config.get("Count", 20)
        sleep = self.config.get("Sleep", 0.1)

        for i in range(count):
            logging.info(f"Running {self.name} iteration {i + 1}")
            time.sleep(sleep)

        self.result = SimpleTestResult(self.name, ResultStatus.PASSED)
        time.sleep(sleep)
