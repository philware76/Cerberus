import logging
from typing import Any, Dict, List

from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
    BaseSpecAnalyser
from Cerberus.pluginService import PluginService


class EquipmentService:
    """Service to manage equipment for a station (role-less storage)."""

    def __init__(self, pluginService: PluginService, db: StorageInterface):
        self.database = db
        self.pluginService = pluginService
        self._attached: List[Dict[str, Any]] = []
        self.reload()

    def reload(self) -> List[Dict[str, Any]]:
        if hasattr(self.database, 'listStationEquipment'):
            self._attached = self.database.listStationEquipment()  # type: ignore[attr-defined]
        else:
            self._attached = []
        return self._attached

    # Registration -----------------------------------------------------------------------------------------------
    def registerEquipment(self, manufacturer: str, model: str, serial: str, version: str,
                          ip: str, port: int, timeout: int, calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:
        return self.database.upsertEquipment(manufacturer, model, serial, version, ip, port, timeout, calibration_date, calibration_due)  # type: ignore[arg-type]

    def registerSigGen(self, typeName: str, serial: str, ip: str, port: int, timeout: int,
                       manufacturer: str = "", version: str = "", calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:
        if not self.pluginService.findEquipType(typeName, BaseSigGen):
            logging.error(f"Type '{typeName}' is not a valid BaseSigGen plugin")
            return None
        return self.registerEquipment(manufacturer or "", typeName, serial, version, ip, port, timeout, calibration_date, calibration_due)

    def registerSpecAn(self, typeName: str, serial: str, ip: str, port: int, timeout: int,
                       manufacturer: str = "", version: str = "", calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:
        if not self.pluginService.findEquipType(typeName, BaseSpecAnalyser):
            logging.error(f"Type '{typeName}' is not a valid BaseSpecAnalyser plugin")
            return None
        return self.registerEquipment(manufacturer or "", typeName, serial, version, ip, port, timeout, calibration_date, calibration_due)

    # Attachment --------------------------------------------------------------------------------------------------
    def attach(self, equipmentId: int) -> bool:
        if hasattr(self.database, 'attachEquipmentToStation') and self.database.attachEquipmentToStation(equipmentId):  # type: ignore[attr-defined]
            logging.info(f"Attached equipment id={equipmentId} to station")
            self.reload()
            return True
        logging.error("attachEquipmentToStation not available or failed on storage backend")
        return False

    # Filtering ---------------------------------------------------------------------------------------------------
    def filterSigGens(self) -> List[Dict[str, Any]]:
        return [e for e in self._attached if self.pluginService.findEquipType(e.get('model', ''), BaseSigGen)]

    def filterSpecAns(self) -> List[Dict[str, Any]]:
        return [e for e in self._attached if self.pluginService.findEquipType(e.get('model', ''), BaseSpecAnalyser)]

    def listAttached(self) -> List[Dict[str, Any]]:
        return list(self._attached)
