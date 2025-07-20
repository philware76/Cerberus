from plugins import hookimpl
from plugins.tests.baseTest import BaseTest

@hookimpl
def createTestPlugin():
    return DynamicRangeTest()

class DynamicRangeTest(BaseTest):
    def __init__(self):
        super().__init__("DynamicRangeTest")
