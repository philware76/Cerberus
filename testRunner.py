import logging

from testManager import TestManager
from plugins.tests.baseTest import BaseTest


class TestRunner:
    def __init__(self, testManager):
        self.testManager: TestManager = testManager

    def runTest(self, test: BaseTest) -> bool:
        logging.warning(f"Running test: {test.name}")

        # Check if the test can be initialized
        if not test.initialise(None):
            logging.error(f"Failed to initialize test: {test.name}")
            return False

        # Check for required equipment
        foundAll, missingEquipment = self.testManager.checkRequirements(test)
        if not foundAll:
            logging.error(f"Missing required equipment for test: {test.name}. Missing: {missingEquipment}")
            return False

        # Run the actual test logic
        test.run()

        logging.info(f"Test {test.name} completed.")

        # Retrieve and log the result
        result = test.getResult()
        logging.info(f"Test {test.name} result: {result}")

        return True
