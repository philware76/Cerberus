from testManager import TestManager
from cmdShells.basePluginShell import BasePluginShell
from cmdShells.baseShell import BaseShell
from cmdShells.common import displayPluginCategory
from plugins.tests.baseTest import BaseTest
from testRunner import TestRunner


class TestsShell(BaseShell):
    intro = "Welcome to Cerberus Test System. Type help or ? to list commands.\n"
    prompt = 'Tests> '

    def __init__(self, manager: TestManager):
        super().__init__()

        self.manager = manager

    def do_list(self, arg):
        """List all of the Tests"""
        displayPluginCategory("Test", self.manager.testPlugins)

    def do_load(self, testName):
        """Loads a test"""
        try:
            test = self.manager.testPlugins[testName]
            TestShell(test).cmdloop()
        except KeyError:
            print(f"Unknown test: {testName}")

class TestShell(BasePluginShell):
    def __init__(self, test: BaseTest, manager: TestManager):
        TestShell.intro = f"Welcome to Cerberus {test.name} Test System. Type help or ? to list commands.\n"
        TestShell.prompt = f"{test.name}> "

        super().__init__(test)
        self.test: BaseTest = test
        self.manager : TestManager = manager

    def do_run(self, arg):
        """Run the loaded test"""
        testRunner = TestRunner(self.manager)
        testRunner.runTest(self.test)