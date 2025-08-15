from abc import abstractmethod

from Cerberus.plugins.equipment.baseEquipment import BaseEquipment


class BaseSigGen(BaseEquipment):
    """
    Base class for all signal generator equipment plugins.
    This class should be extended by specific signal generator equipment plugins.
    """

    def __init__(self, name: str):
        super().__init__(name)

    @abstractmethod
    def setOutputPower(self, level_dBm) -> bool:
        """Sets the output power level (dBm)"""

    @abstractmethod
    def setFrequency(self, frequencyMHz: int) -> bool:
        """Sets the frequenecy (MHz)"""

    @abstractmethod
    def enablePower(self, state: bool) -> bool:
        """Turns on or off the output power"""
