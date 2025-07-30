from Cerberus.cerberusManager import CerberusManager
from Cerberus.executor import Executor
from Cerberus.plugins.tests.baseTestResult import ResultStatus

manager: CerberusManager


def test_CerberusManager():
    global manager

    manager = CerberusManager()
    assert len(manager.missingPlugins) == 0


def test_Executor():
    testRunner = Executor(manager)

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
