import logging
from typing import cast

from Cerberus.cmdShells.basePluginShell import BasePluginShell
from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.executor import Executor
from Cerberus.manager import Manager
from Cerberus.plugins.tests.baseTest import BaseTest


class TestsShell(PluginsShell):
    def __init__(self, manager: Manager):
        pluginService = manager.pluginService
        super().__init__(manager, pluginService.testPlugins, "Test")


class TestShell(BasePluginShell):
    def __init__(self, test: BaseTest, manager: Manager):
        TestShell.intro = f"Welcome to Cerberus {test.name} Test shell. Type help or ? to list commands.\n"
        TestShell.prompt = f"{test.name}> "

        super().__init__(test, manager)

    def do_run(self, arg):
        """Run the loaded test"""
        if self.manager.product is None:
            logging.warning("There is no selected product for this test, did you forget to select?")

        testRunner = Executor(self.manager.pluginService)
        testRunner.runTest(cast(BaseTest, self.plugin), product=self.manager.product)

    def do_saveSettings(self, arg):
        """Save the settings to the database"""
        db = self.manager.db
        db.save_tests([self.plugin])
