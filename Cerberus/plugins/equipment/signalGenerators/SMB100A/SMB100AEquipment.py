import logging
from typing import Any

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.equipment.visaInitMixin import VisaInitMixin


@hookimpl
@singleton
def createEquipmentPlugin():
    return SMB100A()


class SMB100A(BaseSigGen, VISADevice, VisaInitMixin):
    def __init__(self):
        BaseSigGen.__init__(self, "SMB100A")
        VisaInitMixin.__init__(self)

    def initialise(self, init: Any | None = None) -> bool:
        if self._initialised:
            logging.debug(f"{self.name} is already initialised.")
            return True

        if not self._visa_initialise(init):
            return False

        self._initialised = BaseSigGen.initialise(self)
        return self._initialised

    def finalise(self) -> bool:
        self._visa_finalise()
        return BaseSigGen.finalise(self)

    # Abstract commands --------------------------------------------------------------------------------------------
    def setOutputPower(self, level_dBm) -> bool:
        """Sets the output power (dBm)"""
        return self.set_power(level_dBm)

    def setFrequency(self, frequencyMHz: int) -> bool:
        """Sets the output frequency (MHz)"""
        return self.set_freq(frequencyMHz)

    def setPowerState(self, state: bool) -> bool:
        """Turns on or off the output power"""
        if state:
            return self.output_on()
        else:
            return self.output_off()

    # Library commands ---------------------------------------------------------------------------------------------
    def output_on(self) -> bool:
        return self.command('OUTPut:STATe ON')

    def output_off(self) -> bool:
        return self.command('OUTPut:STATe OFF')

    def freq_mode_cw(self) -> bool:
        return self.command('SOURce:FREQuency:MODE CW')

    def set_power(self, power_lvl):
        return self.command(f'SOURce:POWer:LEVel:IMMediate:AMPLitude {power_lvl}')

    def set_freq(self, freq):
        freq = freq * 1e6
        return self.command(f'SOURce:FREQuency:FIXed {freq}')
