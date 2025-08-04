import logging

from Cerberus.chamberService import ChamberService
from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.planService import PlanService
from Cerberus.pluginService import PluginService


class Manager():
    def __init__(self, db: StorageInterface):
        logging.info("Starting TestManager...")
        self.db = db

        self.pluginService = PluginService()
        self.planService = PlanService(self.db)
        self.chamberService = ChamberService(self.db)
    
    def finalize(self):
        """Final cleanup before exiting the application."""
        logging.debug("Finalizing Cerberus manager...")
        
        # Close the database connection if it exists
        if hasattr(self, 'database') and self.db:
            self.db.close()
            logging.debug("Database connection closed.")
        
        # Any other cleanup tasks can be added here
        logging.debug("Cerberus manager finalized.")