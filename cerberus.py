# cerberus/testmanager.py
from PySide6.QtWidgets import QApplication

import logging
import sys

from logConfig import setupLogging
from plugins.tests.baseTest import BaseTest
from testManager import TestManager


def displayPlugins():
    displayPluginCategory("Equipment", manager.equipPlugins)
    displayPluginCategory("Product", manager.productsPlugins)
    displayPluginCategory("Test", manager.testPlugins)


def displayPluginCategory(category_name, plugins):
    logging.info(f"Available {category_name} plugins:")
    for plugin in plugins.values():
        logging.info(f" - {plugin.name}")
    logging.info("")


if __name__ == "__main__":
    setupLogging(logging.DEBUG)

    app = QApplication(sys.argv)

    manager = TestManager()

    displayPlugins()

    test: BaseTest = manager.testPlugins["TxLevelTest"]
    if test:
        print(f"Created test plugin: {test.name}")
    else:
        print("Plugin not found.")

    valid, missing = manager.checkRequirements(test)
    if not valid:
        logging.error(f"Missing {[equip.__name__ for equip in missing]} equipment requirements for {test.name} test")
    else:
        logging.info(f"All required equipment for {test.name} test is available.")

        test.Initialise()
        # await test.run()
        # result = test.getResult()
        # print(f"Test result: {result.name} - {result.status}")
