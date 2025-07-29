from Cerberus.plugins.tests.baseTestResult import ResultStatus
from Cerberus.testManager import TestManager
from Cerberus.testRunner import TestRunner

manager: TestManager


def test_TestManager():
    global manager

    manager = TestManager()
    assert len(manager.missingPlugins) == 0


def test_TestRunner():
    testRunner = TestRunner(manager)

    testName = "Simple Test #1"
    test = manager.findTest(testName)
    assert test is not None

    test.config["Count"] = 100
    test.config["Sleep"] = 0.0

    assert testRunner.runTest(test)

    result = test.getResult()
    assert result is not None
    assert result.name == testName
    assert result.status == ResultStatus.PASSED
