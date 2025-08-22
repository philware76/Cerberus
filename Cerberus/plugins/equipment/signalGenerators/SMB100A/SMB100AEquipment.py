from typing import Any

from numpy.polynomial import Chebyshev

from Cerberus.common import dwell
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

        self.pwrLevel = 0

    def initialise(self, init: Any | None = None) -> bool:
        if not self._visa_initialise(init):
            return False

        coeffs = {'coeffs': [-0.2507963333638481, -0.06964297336077044, -0.019439599548059367, -0.003609709892110792, -0.01340433126881617, -
                             0.01698232865407864, 0.0064792860891761, -0.014997559295771864, 0.004114665375940766], 'domain': [600.0, 3500.0], 'window': [-1.0, 1.0]}

        self.filter = Chebyshev(coeffs['coeffs'], domain=coeffs['domain'], window=coeffs['window'])

        return BaseSigGen.initialise(self)

    def finalise(self) -> bool:
        self._visa_finalise()
        return BaseSigGen.finalise(self)

    # Abstract commands --------------------------------------------------------------------------------------------
    def setOutputPower(self, level_dBm) -> bool:
        """Sets the output power (dBm)"""
        self.pwrLevel = level_dBm
        if self.set_power(level_dBm):
            dwell(0.25)
            return True

        return False

    def setFrequency(self, frequencyMHz: int) -> bool:
        """Sets the output frequency (MHz)"""

        # This bit of code gets the power offset from the calibration data (filter)
        pwrOfset = self.filter(frequencyMHz)
        self.set_power(self.pwrLevel - pwrOfset)

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
