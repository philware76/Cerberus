from typing import Self

from Cerberus.database.baseDB import BaseDB
from Cerberus.logConfig import getLogger
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.pluginService import PluginService

logger = getLogger("Manager")


class Manager():
    def __init__(self, stationId: str, db: BaseDB, status_callback=None):
        logger.info("Starting TestManager...")
        self.product: BaseProduct | None = None
        self.stationId = stationId
        self.db = db
        self.pluginService = PluginService(status_callback=status_callback)
        # Load persisted parameter values for all plugin categories
        self._loadPersistedParameters()

    def __enter__(self) -> Self:
        """Enable use as a context manager (with statement)."""
        return self

    def __exit__(self, exc_type, exc, tb):
        """On exiting the context, finalize the manager.

        Exceptions from the with-block are not suppressed (return False).
        Any errors raised during finalize are logged but ignored so exit
        continues.
        """
        try:
            self.finalize()
        except Exception:
            logger.exception("Exception during Manager.finalize() in __exit__")

        # Do not suppress exceptions from the with-block
        return False

    # ----------------------------------------------------------------------------------------------------------
    def _loadPersistedParameters(self) -> None:
        """Apply any persisted parameter values from GenericDB to discovered plugin instances.

        Behaviour:
          - Iterates all discovered equipment, tests, and products.
          - For each plugin, calls the genericDB load_*_into() method which overwrites existing
            parameter .value fields IF a record exists for that (station_id, plugin_type, plugin_name, group, param).
          - Missing DB rows are ignored (leave defaults intact).
        """
        # Equipment
        for equip in self.pluginService.equipPlugins.values():
            try:
                self.db.load_equipment_into(equip)
            except Exception as ex:
                logger.warning(f"Failed to load persisted params for equipment '{equip.name}': {ex}")

        # Tests
        for test in self.pluginService.testPlugins.values():
            try:
                self.db.load_test_into(test)
            except Exception as ex:
                logger.warning(f"Failed to load persisted params for test '{test.name}': {ex}")

        # Products
        for product in self.pluginService.productPlugins.values():
            try:
                self.db.load_product_into(product)
            except Exception as ex:
                logger.warning(f"Failed to load persisted params for product '{product.name}': {ex}")

        logger.info("Persisted parameters loaded into plugins (equipment/tests/products).")

    # ----------------------------------------------------------------------------------------------------------
    def saveAll(self) -> None:
        """Persist current parameter values for all plugin categories."""
        try:
            self.db.save_equipment(self.pluginService.equipPlugins.values())
            self.db.save_tests(self.pluginService.testPlugins.values())
            self.db.save_products(self.pluginService.productPlugins.values())
            logger.info("All plugin parameters saved to DB.")

        except Exception as ex:
            logger.error(f"Failed to save plugin parameters: {ex}")

    # ----------------------------------------------------------------------------------------------------------
    def finalize(self):
        """Final cleanup before exiting the application."""
        logger.debug("Finalizing Cerberus manager...")

        # Optionally persist before closing
        try:
            self.saveAll()
        except Exception:
            pass

        if self.db:
            try:
                self.db.close()
                logger.debug("Database connection closed.")
            except Exception:
                logger.debug("Database close raised but ignored.")

        logger.debug("Cerberus manager finalized.")
