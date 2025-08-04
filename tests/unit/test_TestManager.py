from Cerberus.executor import Executor
from Cerberus.manager import Manager
from Cerberus.plugins.tests.baseTestResult import ResultStatus

manager: Manager


def test_CerberusManager():
    global manager

    manager = Manager()
    pluginService = manager.pluginService
    assert len(pluginService.missingPlugins) == 0


def test_Executor(manager: Manager):
    pluginService = manager.pluginService
    testRunner = Executor(pluginService)

    testName = "Simple Test #1"
    test = pluginService.findTest(testName)
    assert test is not None

    test.config["Count"] = 100
    test.config["Sleep"] = 0.0

    assert testRunner.runTest(test)

    result = test.getResult()
    assert result is not None
    assert result.name == testName
    assert result.status == ResultStatus.PASSED
