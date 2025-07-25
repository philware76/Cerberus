import logging
from typing import Any, Dict
from plugins.basePlugin import hookimpl, singleton
from plugins.equipment.baseEquipment import Identity
from plugins.equipment.spectrumAnalysers.baseSpecAnalyser import BaseSpecAnalyser
from plugins.equipment.visaDevice import VISADevice


@hookimpl
@singleton
def createEquipmentPlugin():
    return BB60CEquipment()


class BB60CEquipment(BaseSpecAnalyser):
    def __init__(self):
        super().__init__("BB60C Spectrum Analyser")
        self.identity: Identity | None
        self.visa: VISADevice

        self.init = {"Port": 5025, "IPAddress": "127.0.0.1"}

    def initialise(self, init: Any | None = None) -> bool:
        if self.initialised:
            return True

        if init is not None:
            super().initialise(init)

        self.visa = VISADevice(self.init["Port"], self.init["IPAddress"])
        if self.visa.open() is None:
            logging.error("Failed to open the BB60C Spectrum Analyser")
            return False

        self.identity = self.visa.identity()
        if self.identity is not None:
            self.initialised = True
            return True

        return False

    def finalise(self) -> bool:
        if self.visa.close():
            return super().finalise()
        else:
            return False

    def setRBW(self, bandwidth: float) -> bool:
        """Sets the resolution bandwidth"""
        cmd = f'BAND:RES {bandwidth}KHz'
        return self.visa.command(cmd)

    def setVBW(self, bandwidth: float) -> bool:
        cmd = f'BAND:VID {bandwidth}KHz'
        return self.visa.command(cmd)

    def setCentre(self, frequency: float) -> bool:
        cmd = f'FREQ:CENT {frequency}MHz'
        return self.visa.command(cmd)

    def setSpan(self, frequency: float) -> bool:
        cmd = f'FREQ:SPAN {frequency}MHz'
        return self.visa.command(cmd)

    def setStart(self, frequency: float) -> bool:
        '''Sets the start frequency of the spectrum analyser'''
        raise NotImplementedError("setStart")

    def setStop(self, frequency: float) -> bool:
        '''Sets the stop frequency of the spectrum analyser'''
        raise NotImplementedError("setStop")

    def setRefLevel(self, refLevel: float) -> bool:
        '''Sets the power reference level of the spectrum analyser'''
        cmd = f"POW:RLEV {refLevel}"
        return self.visa.command(cmd)

    def setMarker(self, frequency: float) -> bool:
        '''Sets the marker frequency position'''
        raise NotImplementedError("setMarker")

    def getMarker(self) -> float:
        '''Gets the marker value from the spectrum analyser'''
        raise NotImplementedError("getMarker")
