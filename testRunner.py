import logging

from plugins.tests.baseTest import BaseTest


class TestRunner:
    def __init__(self, testManager):
        self.testManager = testManager

    def runTest(self, test: BaseTest) -> bool:
        logging.info(f"Running test: {test.name}")

        # Check if the test can be initialized
        if not test.Initialise():
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
