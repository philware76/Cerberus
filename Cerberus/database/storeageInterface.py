from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

from Cerberus.plan import Plan


class StorageInterface(ABC):
    """Abstract base class for the storage interface required for Cerberus."""

    @abstractmethod
    def close(self):
        """Close the database"""

    @abstractmethod
    def wipeDB(self) -> bool:
        """Wipes the entire database"""

    @abstractmethod
    def saveTestPlan(self, plan: Plan) -> int | None:
        """Save a test plan to the database and return its ID."""

    @abstractmethod
    def set_TestPlanForStation(self, plan_id: int) -> bool:
        """Set the test plan for this station in the database, only if plan_id exists."""

    @abstractmethod
    def get_TestPlanForStation(self) -> Plan | None:
        """Get the test plan for this station from the database using a JOIN."""

    @abstractmethod
    def get_ChamberForStation(self) -> str | None:
        """Get the chamber class name for this station from the database."""

    @abstractmethod
    def set_ChamberForStation(self, chamberType: str) -> bool:
        """Set the chamber class name for this station in the database."""

    @abstractmethod
    def listTestPlans(self) -> list[Tuple[int, Plan]]:
        """List all test plans in the database."""

    @abstractmethod
    def deleteTestPlan(self, plan_id: int) -> bool:
        """Delete a test plan by ID."""

    # --- Equipment Management -------------------------------------------------------------------------------------
    @abstractmethod
    def upsertEquipment(self, equipRole: str, manufacturer: str, model: str, serial: str, version: str,
                        ip: str, port: int, timeout: int, calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:
        """Insert or update an equipment record, returning its ID.
        equipRole: logical role the equipment fulfils (SIGGEN | SPECAN)
        model: plugin / model identifier
        Calibration dates optional (YYYY-MM-DD).
        """

    @abstractmethod
    def assignEquipmentToStation(self, equipRole: str, equipmentId: int) -> bool:
        """Assign an equipment record (by role SIGGEN/SPECAN) to this station."""

    @abstractmethod
    def getStationEquipment(self) -> Dict[str, Dict[str, Any]]:
        """Return mapping of role -> equipment record (roles: SIGGEN, SPECAN)."""
