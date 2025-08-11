from abc import ABC, abstractmethod
from typing import Any


class CommsInterface(ABC):
    """Abstract class to describe basic comms functions"""

    @abstractmethod
    def open(self) -> Any | None:
        """Open the comms device for communication"""

    @abstractmethod
    def close(self) -> bool:
        """Close the device for communication"""

    @abstractmethod
    def write(self, command) -> bool:
        """Write a command to the comms device"""

    @abstractmethod
    def query(self, command: str) -> str | None:
        """Send a command and wait for a reply"""
