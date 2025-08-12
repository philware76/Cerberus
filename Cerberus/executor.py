import logging

from Cerberus.exceptions import TestError
from Cerberus.manager import Manager, PluginService
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import ResultStatus


class Executor:
    """Class that handles executing a single test"""

    def __init__(self, pluginService: PluginService):
        self.pluginService = pluginService

    def runTest(self, test: BaseTest) -> bool:
        """Run a single test"""
        logging.warning(f"Running test: {test.name}")

        # Check if the test can be initialized
        if not test.initialise():
            logging.error(f"Failed to initialize test: {test.name}")
            return False

        # Check for required equipment (not initialised here)
        req_map, missingEquipTypes = self.pluginService.checkRequirements(test)
        if len(missingEquipTypes) > 0:
            logging.error(f"Missing required equipment for test: {test.name}. Missing: {missingEquipTypes}")
            return False

        # Select one instance per required type and initialise now (comms already applied by Manager)
        equip_map: dict[type[BaseEquipment], BaseEquipment] = {}
        for req_type, candidates in req_map.items():
            if not candidates:
                continue
            # Simple policy: pick the first available candidate
            equip = candidates[0]
            if not equip.initialise():
                logging.error(f"Failed to initialise {equip.name}, is it online?")
                return False
            logging.debug(f"{equip.name} has been initialised (online)")
            equip_map[req_type] = equip

        # Provide required equipment to test
        test.provideEquip(equip_map)

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

        return bool(result and result.status == ResultStatus.PASSED)
