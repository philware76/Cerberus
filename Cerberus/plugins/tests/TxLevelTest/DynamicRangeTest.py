from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.tests.baseTest import BaseTest


@hookimpl
@singleton
def createTestPlugin():
    return DynamicRangeTest()

class DynamicRangeTest(BaseTest):
    def __init__(self):
        super().__init__("Tx Level Dynamic Range")
