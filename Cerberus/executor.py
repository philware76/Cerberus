import logging

from Cerberus.cerberusManager import CerberusManager
from Cerberus.exceptions import TestError
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import ResultStatus


class Executor:
    """Class that handles executing a single test"""
    def __init__(self, testManager):
        self.testManager: CerberusManager = testManager

    def runTest(self, test: BaseTest) -> bool:
        """Run a single test"""
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
        try:
            test.run()
        except TestError as e:
            logging.error(f"Failed to run {test.name} with {e}")
        finally:
            test.finalise()

        logging.info(f"Test {test.name} completed.")

        # Retrieve and log the result
        result = test.getResult()
        logging.info(f"Test {test.name} result: {result}")

        return result.status == ResultStatus.PASSED
