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
    def write(self, command):
        """Write a command to the comms device"""

    @abstractmethod
    def read(self, bytes: int) -> str | None:
        """Read x number of bytes from the comms device"""

    @abstractmethod
    def query(self, command: str) -> str | None:
        """Send a command and wait for a reply"""
