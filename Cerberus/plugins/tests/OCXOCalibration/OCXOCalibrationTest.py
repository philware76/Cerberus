from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.tests.baseTest import BaseTest


@hookimpl
@singleton
def createTestPlugin():
    return OCXOCalibrationTest()

class OCXOCalibrationTest(BaseTest):
    def __init__(self):
        super().__init__("OCXO Calibration")
