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
        """Resolve and initialise required equipment then inject into the test.

        Steps:
          1. Query requirements (candidates + missing).
          2. Fail fast if any requirement has zero candidates.
          3. For each required abstract type, attempt to initialise candidates
             in order until one succeeds (selection policy).  If none succeed
             the whole preparation fails.
        """
        reqs = self.pluginService.getRequirements(test)

        if reqs.missing:
            self._log_missing_requirements(test, reqs.missing)
            return False

        equip_map: dict[type[BaseEquipment], BaseEquipment] = {}
        for req_type, candidates in reqs.candidates.items():
            selected = self._initialise_first_online(req_type, candidates, test)
            if selected is None:
                return False

            equip_map[req_type] = selected

        test.provideEquip(equip_map)
        return True

    # --- Helpers -------------------------------------------------------------------------------------------------
    @staticmethod
    def _log_missing_requirements(test: BaseTest, missing: list[type[BaseEquipment]]) -> None:
        missing_names = [t.__name__ for t in missing]
        logging.error(
            f"Missing required equipment for test: {test.name}. Missing: {missing_names}"  # noqa: E501
        )

    def _initialise_first_online(self, req_type: type[BaseEquipment], candidates: list[BaseEquipment], test: BaseTest) -> BaseEquipment | None:
        """Try to initialise each candidate in order; return the first that succeeds.

        Returns None (after logging) if all candidates fail.
        """
        for idx, candidate in enumerate(candidates, start=1):
            if candidate.initialise():
                logging.debug(
                    f"{candidate.name} (#{idx}/{len(candidates)}) initialised for requirement {req_type.__name__}"  # noqa: E501
                )
                return candidate

            logging.warning(
                f"Candidate {candidate.name} (#{idx}/{len(candidates)}) failed to initialise for {req_type.__name__}"  # noqa: E501
            )

        logging.error(
            f"All {len(candidates)} candidates failed for requirement {req_type.__name__} in test {test.name}"  # noqa: E501
        )
        return None

    def runTest(self, test: BaseTest, product: BaseProduct | None) -> bool:
        """Run a single test with an optional pre-configured product injected."""
        logging.debug(f"Running test: {test.name}")

        test.setProduct(product)

        if not test.initialise():
            logging.error(f"Failed to initialize test: {test.name}")
            return False

        if not self._prepare_equipment(test):
            return False

        try:
            test.run()

        except TestError as e:
            logging.error(f"Failed to run {test.name} test with {e}")

        finally:
            test.finalise()

        logging.info("{test.name} test has completed.")

        if test.result is not None:
            logging.info(f"{test.name} test result: {test.result.status}")
            if test.result.log is not None:
                print(test.result.log)

            return test.result.status == ResultStatus.PASSED or \
                test.result.status == ResultStatus.SKIPPED

        else:
            print("Test did not produce and results (?!)")
            return False
