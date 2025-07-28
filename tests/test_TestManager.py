from logConfig import setupLogging
from testManager import TestManager
from testRunner import TestRunner


def test_TestManager():
    setupLogging()
    manager = TestManager()
    assert len(manager.missingPlugins) == 0

    testRunner = TestRunner(manager)

    test = manager.findTest("Simple Test #1")
    assert test is not None

    testRunner.runTest(test)
