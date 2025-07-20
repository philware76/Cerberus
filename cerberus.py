# cerberus/testmanager.py
from PySide6.QtWidgets import QApplication

import logging
import sys

from logConfig import setupLogging
from testManager import TestManager

if __name__ == "__main__":
    setupLogging(logging.DEBUG)

    app = QApplication(sys.argv)

    logging.info("Starting TestManager...")
    manager = TestManager()

    logging.info("Available equipment plugins:")
    for equipment in manager.Equipement.listPlugins():
        logging.info(" - " + equipment)

    logging.info("Available test plugins:")
    for test in manager.Test.listPlugins():
        logging.info(" - " + test)

    test = manager.Test.createPlugin("TxLevelTest")
    if test:
        print(f"Created test plugin: {test.name}")
    else:
        print("Plugin not found.")

    if test:
        test.Initialise()
        test.run()
        result = test.getResult()
        print(f"Test result: {result.name} - {result.status}")