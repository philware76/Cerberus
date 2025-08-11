import logging

from Cerberus.chamberService import ChamberService
from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.equipmentService import EquipmentService
from Cerberus.planService import PlanService
from Cerberus.pluginService import PluginService


class Manager():
    def __init__(self, stationId: str, db: StorageInterface):
        logging.info("Starting TestManager...")
        self.stationId = stationId
        self.db = db

        self.pluginService = PluginService()

        self.planService = PlanService(self.pluginService, self.db)
        self.chamberService = ChamberService(self.pluginService, self.db)
        self.equiService = EquipmentService(self.pluginService, self.db)

        # Load any persisted equipment comms settings for this station
        self._applyPersistedEquipmentComms()

    def _applyPersistedEquipmentComms(self):
        try:
            records = self.db.listStationEquipment()  # type: ignore[attr-defined]
        except Exception as ex:
            logging.error(f"Failed to list station equipment: {ex}")
            return

        if not records:
            logging.debug("No equipment records attached to this station.")
            return

        applied = 0
        for rec in records:
            model = rec['model']
            equip = self.pluginService.findEquipment(model)
            if not equip:
                logging.warning(f"No plugin found for model '{model}'")
                continue

            comms = {
                'IP Address': rec.get('ip_address'),
                'Port': int(rec.get('port', 0)),
                'Timeout': int(rec.get('timeout_ms', 0)),
            }
            equip.initComms(comms)  # type: ignore[attr-defined]
            applied += 1

        logging.info(f"Applied comms parameters to {applied} equipment plugin(s).")

    def finalize(self):
        """Final cleanup before exiting the application."""
        logging.debug("Finalizing Cerberus manager...")

        # Close the database connection if it exists
        if self.db:
            self.db.close()
            logging.debug("Database connection closed.")

        # Any other cleanup tasks can be added here
        logging.debug("Cerberus manager finalized.")
