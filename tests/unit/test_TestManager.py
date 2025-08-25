from Cerberus.executor import Executor
from Cerberus.manager import Manager
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.tests.baseTestResult import ResultStatus


def test_Executor(manager: Manager):
    pluginService = manager.pluginService
    testRunner = Executor(pluginService)
    product = BaseProduct("Product1")

    testName = "Simple Test #1"
    test = pluginService.findTest(testName)
    assert test is not None

    test.config["Count"] = 100
    test.config["Sleep"] = 0.0

    assert testRunner.runTest(test, product)

    result = test.result
    assert result is not None
    assert result.name == testName
    assert result.status == ResultStatus.PASSED
