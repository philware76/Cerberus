import logging
from typing import Any, Dict

from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
    BaseSpecAnalyser
from Cerberus.pluginService import PluginService


class EquipmentService:
    """Service to manage assigned equipment (Signal Generator & Spectrum Analyser) for a station.

    Responsibilities:
    - Assign specific equipment instances (by existing equipment table record) to station.
    - Validate equipment type via plugin registry (ensures correct class type name).
    - Retrieve currently assigned equipment metadata.
    """

    def __init__(self, pluginService: PluginService, db: StorageInterface):
        self.database = db
        self.pluginService = pluginService
        self._assigned: Dict[str, Dict[str, Any]] = {}
        self.loadAssignedEquipment()

    def loadAssignedEquipment(self) -> Dict[str, Dict[str, Any]]:
        """Load equipment assignments (by equipment IDs) from station record."""
        self._assigned = self.database.getStationEquipment()
        return self._assigned

    # --- Assignment Helpers --------------------------------------------------------------------------------------
    def assignSignalGenerator(self, equipId: int) -> bool:
        return self._assignEquipmentId("SIGGEN", equipId)

    def assignSpectrumAnalyser(self, equipId: int) -> bool:
        return self._assignEquipmentId("SPECAN", equipId)

    def _assignEquipmentId(self, role: str, equipId: int):
        if self.database.assignEquipmentToStation(role, equipId):
            logging.info(f"Assigned {role} equipment id={equipId} to station")
            self.loadAssignedEquipment()
            return True
        logging.error(f"Failed to assign {role} equipment id={equipId} to station")
        return False

    # --- Validation -----------------------------------------------------------------------------------------------
    def validateSigGenType(self, name: str) -> bool:
        plugin = self.pluginService.findEquipType(name, BaseSigGen)
        return plugin is not None

    def validateSpecAnalyserType(self, name: str) -> bool:
        plugin = self.pluginService.findEquipType(name, BaseSpecAnalyser)
        return plugin is not None

    # --- Register / Upsert Equipment -----------------------------------------------------------------------------
    def registerSignalGenerator(self, typeName: str, serial: str, ip: str, port: int, timeout: int,
                                manufacturer: str = "", model: str = "", version: str = "",
                                calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:
        if not self.validateSigGenType(typeName):
            logging.error(f"Type '{typeName}' is not a valid BaseSigGen plugin")
            return None
        return self.database.upsertEquipment("SIGGEN", manufacturer, model or typeName, serial, version, ip, port, timeout, calibration_date, calibration_due)

    def registerSpectrumAnalyser(self, typeName: str, serial: str, ip: str, port: int, timeout: int,
                                 manufacturer: str = "", model: str = "", version: str = "",
                                 calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:
        if not self.validateSpecAnalyserType(typeName):
            logging.error(f"Type '{typeName}' is not a valid BaseSpecAnalyser plugin")
            return None
        return self.database.upsertEquipment("SPECAN", manufacturer, model or typeName, serial, version, ip, port, timeout, calibration_date, calibration_due)

    # --- Accessors ------------------------------------------------------------------------------------------------
    def getAssigned(self) -> Dict[str, Dict[str, Any]]:
        return self._assigned.copy()
        return self._assigned.copy()
