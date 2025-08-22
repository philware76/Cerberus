from abc import ABC, abstractmethod

from Cerberus.plugins.equipment.baseEquipment import BaseCommsEquipment


class BasePowerMeter(BaseCommsEquipment, ABC):
    """
    Base class for all power meter equipment plugins.
    This class should be extended by specific spectrum analyser equipment plugins.
    """

    @abstractmethod
    def setFrequency(self, frequencyMHz: float) -> bool:
        """Sets the frequency (MHz) for the measurement"""

    @abstractmethod
    def getPowerReading(self) -> float:
        """Gets the power reading"""
