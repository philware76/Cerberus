from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

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

    # --- Equipment Management (station-centric, role-less) -------------------------------------------------------
    @abstractmethod
    def upsertEquipment(self, manufacturer: str, model: str, serial: str, version: str,
                        ip: str, port: int, timeout: int, calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:
        """Insert or update an equipment record (unique by serial), returning its ID."""

    @abstractmethod
    def attachEquipmentToStation(self, equipmentId: int) -> bool:
        """Attach an equipment record to this station (one station per equipment)."""

    @abstractmethod
    def listStationEquipment(self) -> List[Dict[str, Any]]:
        """Return list of equipment dicts attached to this station."""

    @abstractmethod
    def fetchStationEquipmentByModel(self, model: str) -> Dict[str, Any] | None:
        """Return a single equipment dict for this station matching model, or None if not attached."""

    # --- Calibration Cable Management ---------------------------------------------------------------------------
    @abstractmethod
    def upsertCalCable(self, role: str, serial: str, *, method: str, degree: int,
                       domain: tuple[float, float], coeffs: list[float]) -> int | None:
        """Insert or update calibration cable (unique per station+role). Returns id/marker or None on failure."""

    @abstractmethod
    def fetchCalCable(self, role: str) -> Dict[str, Any] | None:
        """Fetch calibration cable metadata for role ('TX'/'RX') or None."""

    @abstractmethod
    def listCalCables(self) -> List[Dict[str, Any]]:
        """List all calibration cables for this station."""

    @abstractmethod
    def deleteCalCable(self, role: str) -> bool:
        """Delete calibration cable for role; return True if existed."""

    @abstractmethod
    def buildCalCableChebyshev(self, role: str):
        """Return (Chebyshev|None, metadata) for stored cable if method == chebyshev."""

    @abstractmethod
    def buildCalCableLossFn(self, role: str):
        """Return (callable(freq_mhz)->loss or None, metadata)."""
