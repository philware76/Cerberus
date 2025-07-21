from plugins.basePlugin import hookimpl, singleton
from plugins.tests.baseTest import BaseTest

@hookimpl
@singleton
def createTestPlugin():
    return OCXOCalibrationTest()

class OCXOCalibrationTest(BaseTest):
    def __init__(self):
        super().__init__("OCXOCalibrationTest")
