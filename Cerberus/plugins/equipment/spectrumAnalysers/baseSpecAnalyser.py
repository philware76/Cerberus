from abc import ABC, abstractmethod

from Cerberus.plugins.equipment.baseEquipment import (BaseCommsEquipment,
                                                      Identity)


class BaseSpecAnalyser(BaseCommsEquipment, ABC):
    """
    Base class for all spectrum analyser equipment plugins.
    This class should be extended by specific spectrum analyser equipment plugins.
    """

    @abstractmethod
    def setBWS(self, shape: str) -> bool:
        """Set the bandwdith filter shape"""

    @abstractmethod
    def setRBW(self, bandwidthkHz: float) -> bool:
        '''Sets the resolution bandwidth (kHz) of the spectrum analyser'''

    @abstractmethod
    def setVBW(self, bandwidthkHz: float) -> bool:
        '''Sets the visual bandwidth (kHz) of the spectrum analyser'''

    @abstractmethod
    def setCentre(self, frequencyMHz: float) -> bool:
        '''Sets the centre frequency (MHz) of the spectrum analyser'''

    @abstractmethod
    def setRefInput(self, input: str) -> bool:
        """Sets the input reference type - INT or EXT"""

    @abstractmethod
    def setSpan(self, frequencyMHz: float) -> bool:
        '''Sets the span frequency (MHz) of the spectrum analyser'''

    @abstractmethod
    def setStart(self, frequencyMHz: float) -> bool:
        '''Sets the start frequency (MHz) of the spectrum analyser'''

    @abstractmethod
    def setStop(self, frequencyMHz: float) -> bool:
        '''Sets the stop frequency (MHz) of the spectrum analyser'''

    @abstractmethod
    def setRefLevel(self, refLevel: float) -> bool:
        '''Sets the power reference level of the spectrum analyser'''

    @abstractmethod
    def setMarkerPeak(self) -> bool:
        '''Sets the marker to the maximum/peak position'''

    @abstractmethod
    def getMarkerFreq(self) -> float:
        '''Gets the marker frequency value (X)'''

    @abstractmethod
    def getMarkerPower(self) -> float:
        '''Gets the marker power value (X)'''
