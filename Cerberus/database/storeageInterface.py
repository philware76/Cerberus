from abc import ABC, abstractmethod
from typing import Tuple

from Cerberus.plan import Plan


class StorageInterface(ABC):
    """Abstract base class for the storage interface required for Cerberus."""
    @abstractmethod
    def saveTestPlan(self, plan: Plan) -> int:
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
