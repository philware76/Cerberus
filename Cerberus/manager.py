import logging

import iniconfig

from Cerberus.chamberService import ChamberService
from Cerberus.database import Database, dbInfo
from Cerberus.planService import PlanService
from Cerberus.pluginService import PluginService


class Manager():
    def __init__(self):
        logging.info("Starting TestManager...")

        self.loadIni()
        logging.info(f"Cerberus:{self.stationId}")

        self.db = Database(self.stationId, self.dbInfo)

        self.pluginService = PluginService()
        self.planService = PlanService(self.db)
        self.chamberService = ChamberService(self.db)

    def loadIni(self):
        ini = iniconfig.IniConfig("cerberus.ini")
        if ini is None:
            logging.error("Failed to load cerberus.ini file!")
            exit(1)

        self.stationId = ini["cerberus"]["identity"]
        self.dbInfo = dbInfo(
            host=ini["database"]["host"],
            username=ini["database"]["username"],
            password=ini["database"]["password"],
            database=ini["database"]["database"]
        )

    
    def finalize(self):
        """Final cleanup before exiting the application."""
        logging.debug("Finalizing Cerberus manager...")
        
        # Close the database connection if it exists
        if hasattr(self, 'database') and self.db:
            self.db.close()
            logging.debug("Database connection closed.")
        
        # Any other cleanup tasks can be added here
        logging.debug("Cerberus manager finalized.")