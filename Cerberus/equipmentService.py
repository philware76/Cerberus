import logging
from typing import Any

from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.pluginService import PluginService


class EquipmentService:
    """Service to manage equipment for a station (role-less storage)."""

    def __init__(self, pluginService: PluginService, db: StorageInterface):
        self.database = db
        self.pluginService = pluginService
        self._attached: list[dict[str, Any]] = []
        self.reload()

    def reload(self) -> list[dict[str, Any]]:
        if hasattr(self.database, 'listStationEquipment'):
            self._attached = self.database.listStationEquipment()  # type: ignore[attr-defined]
        else:
            self._attached = []
        return self._attached

    # Attachment --------------------------------------------------------------------------------------------------
    def attach(self, equipmentId: int) -> bool:
        if hasattr(self.database, 'attachEquipmentToStation') and self.database.attachEquipmentToStation(equipmentId):  # type: ignore[attr-defined]
            logging.info(f"Attached equipment id={equipmentId} to station")
            self.reload()
            return True
        logging.error("attachEquipmentToStation not available or failed on storage backend")
        return False

    def listAttached(self) -> list[dict[str, Any]]:
        return list(self._attached)
