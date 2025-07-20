from plugins import hookimpl
from plugins.tests.baseTest import BaseTest

@hookimpl
def createTestPlugin():
    return OCXOCalibrationTest()

class OCXOCalibrationTest(BaseTest):
    def __init__(self):
        super().__init__("OCXOCalibrationTest")
