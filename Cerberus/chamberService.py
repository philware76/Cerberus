import logging

from Cerberus.database import Database
from Cerberus.plugins.equipment.chambers.baseChamber import BaseChamber


class ChamberService:
    def __init__(self, db: Database):
        self.chamber: BaseChamber
        self.database = db
        self.loadChamber()

    def loadChamber(self):
        """Load the chamber class for this station from the database."""
        self.chamber = self.database.get_ChamberForStation()
        if self.chamber:
            logging.debug(f"Chamber class loaded: {self.chamber}")
        else:
            logging.warning("No chamber class found for this station.")

    def saveChamber(self, chamberName: str) -> bool:
        """Save the chamber class for this station in the database.
        Returns True if set successfully, False otherwise.
        """
        if not chamberName:
            logging.error("Chamber class name cannot be empty.")
            return False

        # Check if chamber_class is a valid BaseChamber subclass
        chamber_plugin = self.findEquipment(chamberName)
        if not chamber_plugin or not isinstance(chamber_plugin, BaseChamber):
            logging.error(f"Chamber class '{chamberName}' is not a valid BaseChamber subclass.")
            return False

        if self.database.set_ChamberForStation(chamberName):
            logging.info(f"Chamber class set to: {chamberName}")
            return True
        else:
            logging.error(f"Failed to set chamber class to: {chamberName}")
            return False
