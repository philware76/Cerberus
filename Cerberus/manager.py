import logging

from Cerberus.database.baseDB import BaseDB
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.pluginService import PluginService


class Manager():
    def __init__(self, stationId: str, db: BaseDB):
        logging.info("Starting TestManager...")
        self.product: BaseProduct | None = None
        self.stationId = stationId
        self.db = db

        self.pluginService = PluginService()
        # Future service initialisation commented for now
        # self.planService = PlanService(self.pluginService, self.db)
        # self.chamberService = ChamberService(self.pluginService, self.db)
        # self.calCableService = CalCableService(self.pluginService, self.db)

        # Load persisted parameter values for all plugin categories
        self._loadPersistedParameters()

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
                logging.warning(f"Failed to load persisted params for equipment '{equip.name}': {ex}")

        # Tests
        for test in self.pluginService.testPlugins.values():
            try:
                self.db.load_test_into(test)
            except Exception as ex:
                logging.warning(f"Failed to load persisted params for test '{test.name}': {ex}")

        # Products
        for product in self.pluginService.productPlugins.values():
            try:
                self.db.load_product_into(product)
            except Exception as ex:
                logging.warning(f"Failed to load persisted params for product '{product.name}': {ex}")

        logging.info("Persisted parameters loaded into plugins (equipment/tests/products).")

    # ----------------------------------------------------------------------------------------------------------
    def saveAll(self) -> None:
        """Persist current parameter values for all plugin categories."""
        try:
            self.db.save_equipment(self.pluginService.equipPlugins.values())
            self.db.save_tests(self.pluginService.testPlugins.values())
            self.db.save_products(self.pluginService.productPlugins.values())
            logging.info("All plugin parameters saved to DB.")

        except Exception as ex:
            logging.error(f"Failed to save plugin parameters: {ex}")

    # ----------------------------------------------------------------------------------------------------------
    def finalize(self):
        """Final cleanup before exiting the application."""
        logging.debug("Finalizing Cerberus manager...")

        # Optionally persist before closing
        try:
            self.saveAll()
        except Exception:
            pass

        if self.db:
            try:
                self.db.close()
                logging.debug("Database connection closed.")
            except Exception:
                logging.debug("Database close raised but ignored.")

        logging.debug("Cerberus manager finalized.")
