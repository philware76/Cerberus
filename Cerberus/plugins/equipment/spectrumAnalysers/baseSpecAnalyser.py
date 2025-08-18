from abc import ABC, abstractmethod

from Cerberus.plugins.equipment.powerMeters.basePowerMeters import \
    BasePowerMeter


class BaseSpecAnalyser(BasePowerMeter, ABC):
    """Base class for all spectrum analyser equipment plugins.

    Inherits from :class:`BasePowerMeter` so that any concrete spectrum analyser
    implementation automatically satisfies the power meter interface
    (``setFrequency`` / ``getPowerReading``). This reflects that a spectrum
    analyser can perform the basic power measurement functions of a standalone
    power meter.
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
