from abc import ABC, abstractmethod

from Cerberus.plan import Plan


class StorageInterface(ABC):
    """Abstract base class for the storage interface required for Cerberus."""
    @abstractmethod
    def saveTestPlan(self, plan: Plan) -> int:
        """Save a test plan to the database and return its ID."""
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod    
    def set_TestPlanForStation(self, plan_id: int) -> bool:
        """Set the test plan for this station in the database, only if plan_id exists."""
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_TestPlanForStation(self) -> Plan:
        """Get the test plan for this station from the database using a JOIN."""
        raise NotImplementedError("This method should be overridden by subclasses.")

    @abstractmethod
    def get_ChamberForStation(self) -> str | None:
        """Get the chamber class name for this station from the database."""
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod
    def set_ChamberForStation(self, chamberType: str) -> bool:
        """Set the chamber class name for this station in the database."""
        raise NotImplementedError("This method should be overridden by subclasses.")
    
    @abstractmethod    
    def listTestPlans(self) -> list[Plan]:
        """List all test plans in the database."""
        raise NotImplementedError("This method should be overridden by subclasses.")
