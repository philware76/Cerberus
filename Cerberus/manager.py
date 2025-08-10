import logging

from Cerberus.chamberService import ChamberService
from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.equipmentService import EquipmentService
from Cerberus.planService import PlanService
from Cerberus.pluginService import PluginService


class Manager():
    def __init__(self, db: StorageInterface):
        logging.info("Starting TestManager...")
        self.db = db

        self.pluginService = PluginService()
        self.planService = PlanService(self.pluginService, self.db)
        self.chamberService = ChamberService(self.pluginService, self.db)
        self.equiService = EquipmentService(self.pluginService, self.db)

    def finalize(self):
        """Final cleanup before exiting the application."""
        logging.debug("Finalizing Cerberus manager...")

        # Close the database connection if it exists
        if self.db:
            self.db.close()
            logging.debug("Database connection closed.")

        # Any other cleanup tasks can be added here
        logging.debug("Cerberus manager finalized.")
