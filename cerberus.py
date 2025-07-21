# cerberus/testmanager.py
from PySide6.QtWidgets import QApplication

import logging
import sys

from logConfig import setupLogging
from plugins.tests.baseTest import BaseTest
from testManager import TestManager

def displayPlugins():
    displayEquipment()
    displayTests()

def displayEquipment():
    logging.info("Available equipment plugins:")
    for equipment in manager.Equipment:
        logging.info(" - " + equipment.name)

def displayTests():
    logging.info("Available test plugins:")
    for test in manager.Tests:
        logging.info(" - " + test.name)

if __name__ == "__main__":
    setupLogging(logging.DEBUG)

    app = QApplication(sys.argv)

    manager = TestManager()

    displayPlugins()

    test : BaseTest = manager.TestPlugins.getPlugin("TxLevelTest")
    if test:
        print(f"Created test plugin: {test.name}")
    else:
        print("Plugin not found.")

    equipment = manager.checkRequirements(test)
    if not equipment:
        logging.error(f"Curent equipment does not meet the requirements for {test.name}")
    else:
        logging.info(f"All required equipment for {test.name} is available.")

        test.Initialise()
        # await test.run()
        # result = test.getResult()
        # print(f"Test result: {result.name} - {result.status}")