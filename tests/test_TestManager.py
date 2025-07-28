from testManager import TestManager
from testRunner import TestRunner


def test_TestManager():
    manager = TestManager()
    testRunner = TestRunner(manager)

    testRunner.runTest(manager.testPlugins["SimpleTest"])
