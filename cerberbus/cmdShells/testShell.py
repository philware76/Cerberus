from typing import Type, cast
from cmdShells.pluginsShell import PluginsShell
from testManager import TestManager
from cmdShells.common import displayPluginCategory, getInt
from cmdShells.baseShell import BaseShell
from cmdShells.basePluginShell import BasePluginShell
from plugins.tests.baseTest import BaseTest
from testRunner import TestRunner



class TestsShell(PluginsShell):
    def __init__(self, manager:TestManager):
        super().__init__(manager, manager.testPlugins, "Test")


class TestShell(BasePluginShell):
    def __init__(self, test: BaseTest, manager: TestManager):
        TestShell.intro = f"Welcome to Cerberus {test.name} Test System. Type help or ? to list commands.\n"
        TestShell.prompt = f"{test.name}> "

        super().__init__(test, manager)
        
    def do_run(self, arg):
        """Run the loaded test"""
        testRunner = TestRunner(self.manager)
        testRunner.runTest(cast(Type[BaseTest], self.plugin))