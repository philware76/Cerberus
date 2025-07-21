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
    displayPluginCategory("Product", manager.productsPlugins)
    displayPluginCategory("Test", manager.testPlugins)


def displayPluginCategory(category_name, plugins):
    logging.info(f"Available {category_name} plugins:")
    for plugin in plugins.values():
        logging.info(f" - {plugin.name}")

    logging.info("")


class Shell(cmd.Cmd):
    intro = "Welcome to Cerberus Test System. Type help or ? to list commands.\n"
    prompt = 'Cerberus> '

    def do_quit(self, arg):
        """Quit Cerberus shell and exit the application"""
        print("Goodbye")
        exit(0)

    def do_exit(self, arg):
        """Exit Cerberus shell and exit the application"""
        self.do_quit(arg)

    def do_list(self, arg):
        """List all of the supported Equipment, Products and Tests"""
        displayPlugins()

    def do_run(self, testName):
        """Runs a test, after checking the requirements are valid"""
        self.runTest(testName)

    def runTest(self, testName):
        try:
            test = manager.testPlugins[testName]
            testRunner.runTest(test)
        except KeyError as e:
            print(f"Unknown test: {testName}")


if __name__ == "__main__":
    setupLogging(logging.DEBUG)

    app = QApplication(sys.argv)
    manager = TestManager()
    testRunner = TestRunner(manager)

    Shell().cmdloop()
