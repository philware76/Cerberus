from abc import abstractmethod

from Cerberus.plugins.equipment.baseEquipment import BaseCommsEquipment


class BaseSigGen(BaseCommsEquipment):
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
    def setPowerState(self, state: bool) -> bool:
        """Turns on or off the output power"""
