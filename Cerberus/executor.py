import logging

from Cerberus.exceptions import TestError
from Cerberus.manager import PluginService
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import ResultStatus


class Executor:
    """Class that handles executing a single test"""

    def __init__(self, pluginService: PluginService):
        self.pluginService = pluginService

    def _prepare_equipment(self, test: BaseTest) -> bool:
        """Resolve requirements, select, initialise equipment and inject into the test."""
        # Get requirements (candidates, missing, and default selection in one call)
        reqs = self.pluginService.getRequirements(test)
        if len(reqs.missing) > 0:
            missing_names = [t.__name__ for t in reqs.missing]
            logging.error(f"Missing required equipment for test: {test.name}. Missing: {missing_names}")
            return False

        # Initialise selected equipment instances now
        equip_map: dict[type[BaseEquipment], BaseEquipment] = {}
        for req_type, equip in reqs.selection.items():
            if not equip.initialise():
                logging.error(f"Failed to initialise {equip.name}, is it online?")
                return False

            logging.debug(f"{equip.name} has been initialised (online)")
            equip_map[req_type] = equip

        # Provide required equipment to test
        test.provideEquip(equip_map)
        return True

    def runTest(self, test: BaseTest, product: BaseProduct) -> bool:
        """Run a single test with an optional pre-configured product injected."""
        logging.debug(f"Running test: {test.name}")

        test.provideProduct(product)

        if not test.initialise():
            logging.error(f"Failed to initialize test: {test.name}")
            return False

        if not self._prepare_equipment(test):
            return False

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
