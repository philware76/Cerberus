import logging

from Cerberus.exceptions import TestError
from Cerberus.manager import Manager
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import ResultStatus


class Executor:
    """Class that handles executing a single test"""
    def __init__(self, manager):
        self.manager: Manager = manager

    def runTest(self, test: BaseTest) -> bool:
        """Run a single test"""
        logging.warning(f"Running test: {test.name}")

        # Check if the test can be initialized
        if not test.initialise():
            logging.error(f"Failed to initialize test: {test.name}")
            return False

        # Check for required equipment
        foundEquip, missingEquipTypes = self.manager.checkRequirements(test)
        if len(missingEquipTypes) > 0:
            logging.error(f"Missing required equipment for test: {test.name}. Missing: {missingEquipTypes}")
            return False
        
        # check if required equipment is online
        for equip in foundEquip:
            if not equip.initialise():
                logging.error(f"Failed to initailise {equip.name}, is it online?")
                return False
            else:
                logging.debug(f"{equip.name} has been initialised (online)")

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
