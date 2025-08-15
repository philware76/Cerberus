import logging
from typing import Any

from Cerberus.exceptions import EquipmentError
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.baseCommsEquipment import BaseCommsEquipment
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
        BaseSpecAnalyser.__init__(self, "BB60C")
        VisaInitMixin.__init__(self)

    def initialise(self, init: Any | None = None) -> bool:
        if self._initialised:
            logging.debug(f"{self.name} is already initialised.")
            return True

        if not self._visa_initialise(init):
            return False

        self._initialised = BaseCommsEquipment.initialise(self)
        return self._initialised

    # This overrides the VISA operationComplete version
    def operationComplete(self) -> bool:
        logging.debug("Waiting for operation complete...")

        resp = self.query("*OPC?")
        if resp is None:
            logging.debug("Failed to get response from *OPC?")
            return False

        try:
            complete = int(resp)
            logging.debug(f"{self.resource} - *OPC? => {complete}")
            if complete == 1:
                return True

        except ValueError:
            logging.error(f"{self.resource} Invalid response from *OPC? [{resp}]")
            return False

        raise EquipmentError("Failed to get operation complete")

    def finalise(self) -> bool:
        self._visa_finalise()
        return BaseSpecAnalyser.finalise(self)

    def setBWS(self, shape: str) -> bool:
        if shape not in ['FLAT', 'NUTT', 'GAUS']:
            raise EquipmentError(f"Invalid input setting: {input}. Must be either INT or EXT")

        cmd = f'ABND:SHAP {shape}'
        return self.command(cmd)

    def setRefInput(self, input: str) -> bool:
        if input not in ['INT', 'EXT']:
            raise EquipmentError(f"Invalid input setting: {input}. Must be either INT or EXT")

        cmd = f'ROSC:SOUR {input}'
        return self.command(cmd)

    def setRBW(self, bandwidthkHz: float) -> bool:
        cmd = f'BAND:RES {bandwidthkHz}KHz'
        return self.command(cmd)

    def setVBW(self, bandwidthkHz: float) -> bool:
        cmd = f'BAND:VID {bandwidthkHz}KHz'
        return self.command(cmd)

    def setCentre(self, frequencyMHz: float) -> bool:
        cmd = f'FREQ:CENT {frequencyMHz}MHz'
        return self.command(cmd)

    def setSpan(self, frequencyMHz: float) -> bool:
        cmd = f'FREQ:SPAN {frequencyMHz}MHz'
        return self.command(cmd)

    def setStart(self, frequencyMHz: float) -> bool:
        '''Sets the start frequency of the spectrum analyser'''
        raise NotImplementedError("setStart")

    def setStop(self, frequencyMHz: float) -> bool:
        '''Sets the stop frequency of the spectrum analyser'''
        raise NotImplementedError("setStop")

    def setRefLevel(self, refLevel: float) -> bool:
        '''Sets the power reference level of the spectrum analyser'''
        cmd = f"POW:RLEV {refLevel}"
        return self.command(cmd)

    def setMarker(self, frequencyMHz: float) -> bool:
        '''Sets the marker frequency position'''
        raise NotImplementedError("setMarker")

    def getMaxMarker(self) -> float:
        '''Gets the marker value from the spectrum analyser'''
        self.write("CALC:MARK:MAX")
        resp = self.query("CALC:MARK:Y?")
        return float(resp)
