from Cerberus.exceptions import TestError
from Cerberus.logConfig import getLogger
from Cerberus.manager import PluginService
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import ResultStatus

logger = getLogger("executor")


class Executor:
    """Class that handles executing a single test with cached equipment selection."""

    def __init__(self, pluginService: PluginService):
        self.pluginService = pluginService
        # Lazy import to avoid any potential circular import
        from Cerberus.requiredEquipment import \
            RequiredEquipment  # local import
        self.required_equipment = RequiredEquipment(pluginService)

    def flushEquipmentCache(self) -> None:
        """Manually clear the equipment cache (force rediscovery next run)."""
        self.required_equipment.flush_cache()

    def runTest(self, test: BaseTest, product: BaseProduct | None, flush_cache: bool = False) -> bool:
        """Run a single test with an optional pre-configured product injected.

        Args:
            test: Test instance to run.
            product: Optional product instance.
            flush_cache: If True, force a fresh search for all equipment (ignore cache for this run).
        """
        logger.debug(f"Running test: {test.name}")

        test.setProduct(product)

        if not test.initialise():
            logger.error(f"Failed to initialize test: {test.name}")
            return False

        if flush_cache:
            logger.debug("Flush cache flag set; clearing equipment cache before preparation")
            self.required_equipment.flush_cache()

        if not self.required_equipment.prepare(test, force_refresh=False):
            return False

        try:
            test.run()
        except TestError as e:
            logger.error(f"Failed to run {test.name} test with {e}")
        finally:
            test.finalise()

        logger.info(f"{test.name} test has completed.")

        if test.result is not None:
            logger.info(f"{test.name} test result: {test.result.status}")
            if test.result.log is not None:
                print(test.result.log)

            # Save test result to database if available
            self._save_test_result_to_database(test)

            return test.result.status in (ResultStatus.PASSED, ResultStatus.SKIPPED)

        print("Test did not produce any results (?!)")
        return False

    def _save_test_result_to_database(self, test: BaseTest) -> None:
        """Save test result to database if a database is available.

        Args:
            test: The completed test with results
        """
        try:
            # Try to get database from the plugin service
            database = getattr(self.pluginService, 'database', None)
            if database is None:
                logger.debug("No database available, skipping test result save")
                return

            if test.result is None:
                logger.warning(f"Test {test.name} has no result to save")
                return

            # Save the test result
            result_id = database.save_test_result(test.result)
            logger.info(f"Saved test result for {test.name} with ID: {result_id}")

        except Exception as e:
            # Don't fail the test if database save fails
            logger.warning(f"Failed to save test result for {test.name}: {e}")
            logger.debug("Test result save failure details:", exc_info=True)
