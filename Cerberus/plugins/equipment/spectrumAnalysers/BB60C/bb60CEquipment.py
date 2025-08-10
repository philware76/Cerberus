import logging
from typing import Any

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
    BaseSpecAnalyser
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.equipment.visaInitMixin import VisaInitMixin


@hookimpl
@singleton
def createEquipmentPlugin():
    return BB60C()


class BB60C(BaseSpecAnalyser, VISADevice, VisaInitMixin):
    def __init__(self):
        BaseSpecAnalyser.__init__(self, "BB60C Spectrum Analyser")
        VisaInitMixin.__init__(self)

    def initialise(self, init: Any | None = None) -> bool:
        if self._initialised:
            logging.debug(f"{self.name} is already initialised.")
            return True

        if not self._visa_initialise(init):
            return False

        self._initialised = BaseEquipment.initialise(self)
        return self._initialised

    def finalise(self) -> bool:
        self._visa_finalise()
        return BaseSpecAnalyser.finalise(self)

    def setRBW(self, bandwidth: float) -> bool:
        cmd = f'BAND:RES {bandwidth}KHz'
        return self.checkSend(cmd)

    def setVBW(self, bandwidth: float) -> bool:
        cmd = f'BAND:VID {bandwidth}KHz'
        return self.checkSend(cmd)

    def setCentre(self, frequency: float) -> bool:
        cmd = f'FREQ:CENT {frequency}MHz'
        return self.checkSend(cmd)

    def setSpan(self, frequency: float) -> bool:
        cmd = f'FREQ:SPAN {frequency}MHz'
        return self.checkSend(cmd)

    def setStart(self, frequency: float) -> bool:
        '''Sets the start frequency of the spectrum analyser'''
        raise NotImplementedError("setStart")

    def setStop(self, frequency: float) -> bool:
        '''Sets the stop frequency of the spectrum analyser'''
        raise NotImplementedError("setStop")

    def setRefLevel(self, refLevel: float) -> bool:
        '''Sets the power reference level of the spectrum analyser'''
        cmd = f"POW:RLEV {refLevel}"
        return self.checkSend(cmd)

    def setMarker(self, frequency: float) -> bool:
        '''Sets the marker frequency position'''
        raise NotImplementedError("setMarker")

    def getMarker(self) -> float:
        '''Gets the marker value from the spectrum analyser'''
        raise NotImplementedError("getMarker")
