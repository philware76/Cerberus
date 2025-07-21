from abc import ABC, abstractmethod
from plugins.equipment.baseEquipment import BaseEquipment, Identity


class BaseSpecAnalyser(BaseEquipment):
    """
    Base class for all spectrum analyser equipment plugins.
    This class should be extended by specific spectrum analyser equipment plugins.
    """

    def __init__(self, name: str):
        super().__init__(name)

    @abstractmethod
    def getIdentity(self) -> Identity:
        '''Gets the *IDN? string from the'''

    @abstractmethod
    def setRBW(self, bandwidth: float) -> bool:
        '''Sets the resolution bandwidth of the spectrum analyser'''

    @abstractmethod
    def setVBW(self, bandwidth: float) -> bool:
        '''Sets the visual bandwidth of the spectrum analyser'''

    @abstractmethod
    def setCentre(self, frequency: float) -> bool:
        '''Sets the centre frequency of the spectrum analyser'''

    @abstractmethod
    def setSpan(self, frequency: float) -> bool:
        '''Sets the span frequency of the spectrum analyser'''

    @abstractmethod
    def setStart(self, frequency: float) -> bool:
        '''Sets the start frequency of the spectrum analyser'''

    @abstractmethod
    def setStop(self, frequency: float) -> bool:
        '''Sets the stop frequency of the spectrum analyser'''

    @abstractmethod
    def setRefLevel(self, refLevel: float) -> bool:
        '''Sets the power reference level of the spectrum analyser'''

    @abstractmethod
    def setMarker(self, frequency: float) -> bool:
        '''Sets the marker frequency position'''

    @abstractmethod
    def getMarker(self) -> float:
        '''Gets the marker value from the spectrum analyser'''
