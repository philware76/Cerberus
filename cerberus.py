# cerberus/testmanager.py
from PySide6.QtWidgets import QApplication

import logging
import sys
import cmd

from logConfig import setupLogging
from plugins.tests.baseTest import BaseTest
from testManager import TestManager
from testRunner import TestRunner


def displayPlugins():
    displayPluginCategory("Equipment", manager.equipPlugins)
    displayPluginCategory("Product", manager.productPlugins)
    displayPluginCategory("Test", manager.testPlugins)


def displayPluginCategory(category_name, plugins):
    logging.info(f"Available {category_name} plugins:")
    for name, plugin in plugins.items():
        logging.info(f" - {name}: '{plugin.name}'")

    logging.info("")


class EquipShell(cmd.Cmd):
    intro = "Welcome to Cerberus Equipment System. Type help or ? to list commands.\n"
    prompt = 'Equipment> '

    def do_exit(self, arg):
        """Exit the Cerberus Equipment shell"""
        return True

    def do_list(self, arg):
        """List all of the Equipment"""
        displayPluginCategory("Equipment", manager.equipPlugins)


class ProductShell(cmd.Cmd):
    intro = "Welcome to Cerberus Product System. Type help or ? to list commands.\n"
    prompt = 'Product> '

    def do_exit(self, arg):
        """Exit the Cerberus Product shell"""
        return True

    def do_list(self, arg):
        """List all of the Products"""
        displayPluginCategory("Product", manager.productPlugins)


class TestShell(cmd.Cmd):
    def __init__(self, test):
        TestShell.intro = f"Welcome to Cerberus {test.name} Test System. Type help or ? to list commands.\n"
        TestShell.prompt = f"{test.name}> "

        super().__init__()
        self.test = test

    def do_exit(self, arg):
        """Exit the Cerberus {test.name} shell"""
        return True

    def do_run(self, arg):
        testRunner.runTest(self.test)


class TestsShell(cmd.Cmd):
    intro = "Welcome to Cerberus Test System. Type help or ? to list commands.\n"
    prompt = 'Tests> '

    def do_exit(self, arg):
        """Exit the Cerberus Test shell"""
        return True

    def do_list(self, arg):
        """List all of the Tests"""
        displayPluginCategory("Test", manager.testPlugins)

    def do_load(self, testName):
        """Loads a test"""
        try:
            test = manager.testPlugins[testName]
            TestShell(test).cmdloop()
        except KeyError:
            print(f"Unknown test: {testName}")


class Shell(cmd.Cmd):
    intro = "Welcome to Cerberus Test System. Type help or ? to list commands.\n"
    prompt = 'Cerberus> '

    def do_quit(self, arg):
        """Quit Cerberus shell and exit the application"""
        print("Goodbye")
        exit(0)

    def do_equipment(self, arg):
        """Go into the Equipment shell subsystem"""
        EquipShell().cmdloop()

    def do_products(self, arg):
        """Go into the Product shell subsystem"""
        ProductShell().cmdloop()

    def do_tests(self, arg):
        """Go into the Test shell subsystem"""
        TestsShell().cmdloop()


if __name__ == "__main__":
    setupLogging(logging.DEBUG)

    app = QApplication(sys.argv)
    manager = TestManager()
    testRunner = TestRunner(manager)

    Shell().cmdloop()
