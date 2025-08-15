import logging
from typing import Any

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.equipment.visaInitMixin import VisaInitMixin


@hookimpl
@singleton
def createEquipmentPlugin():
    return VSG60C()


class VSG60C(BaseSigGen, VISADevice, VisaInitMixin):
    def __init__(self):
        BaseSigGen.__init__(self, "VSG60")
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
        return BaseSigGen.finalise(self)

    # --------------------------------------------------------------------------------------------------------------
    def setOutputPower(self, level_dBm) -> bool:
        """Sets the output power (dBm)"""
        return self.set_power(level_dBm)

    def setFrequency(self, frequencyMHz: int) -> bool:
        """Sets the output frequency (MHz)"""
        return self.set_freq(frequencyMHz)

    def enablePower(self, state: bool) -> bool:
        """Turns on or off the output power"""
        if state:
            return self.output_on()
        else:
            return self.output_off()

    # Library commands ---------------------------------------------------------------------------------------------
    def trigger(self) -> bool:
        return self.command('*TRG')

    def output_on(self) -> bool:
        return self.command('OUTPUT ON')

    def output_off(self) -> bool:
        return self.command('OUTPUT OFF')

    def Mod_on(self) -> bool:
        return self.command('OUTPUT:MOD ON')

    def Mod_off(self) -> bool:
        return self.command('OUTPUT:MOD OFF')

    def set_freq(self, freq):
        return self.command(f'FREQ {freq}MHz')

    def get_freq(self) -> str | None:
        return self.query('FREQ?')

    def set_freq_step(self, freq):
        return self.command(f'FREQ:STEP {freq}MHz')

    def set_power(self, power_lvl):
        return self.command(f'POW {power_lvl}')

    def get_power(self) -> bool:
        return self.command('POW?')

    def set_power_step(self, power_step):
        return self.command(f'POW:STEP {power_step}')

    def stream_output(self, bool):
        return self.command(f'STREAMING {bool}')

    def set_stream_rate(self, freq):
        return self.command(f'STREAM:SRAT {freq}MHz')

    def set_iq_scale(self, scale):
        return self.command(f'STREAM:IQ:SCALE {scale}')

    def load_iq(self, file, type):
        if type not in ['WAV', '16BIT', '32BIT']:
            logging.debug('ERR in file type command\nload_iq function accepts WAV,16BIT,32BIT')
            return

        if type == '16BIT':
            type = 'BINSC'
        if type == '32BIT':
            type = 'BINFC'

        return self.command(f'STREAM:WAV:LOAD:{type} "{file}"')

    def unload_iq(self) -> bool:
        return self.command('STREAM:WAV:UNLOAD')

    def arb_state(self, bool):
        return self.command(f'RAD:ARB {bool}')

    def arb_load_iq(self, file, type):
        if type not in ['WAV', '16BIT', '32BIT']:
            logging.debug('ERR in file type command\nload_iq function accepts WAV,16BIT,32BIT')
            return

        if type == '16BIT':
            type = 'BINSC'
        if type == '32BIT':
            type = 'BINFC'

        return self.command(f'RAD:ARB:WAV:LOAD:{type} "{file}"')

    def arb_mode(self, mode):
        return self.command(f'RAD:ARB:TRIG:TYPE {mode}')

    def arb_sample_rate(self, freq):
        return self.command(f'RAD:ARB:SRAT {freq}MHz')

    def arb_iq_scale(self, scale):
        return self.command(f'RAD:ARB:IQ:SCALE {scale}')

    def arb_auto_scale(self, bool):
        return self.command(f'RAD:ARB:IQ:SCALE:AUTO {bool}')

    def arb_unload(self) -> bool:
        return self.command('RAD:ARB:WAV:UNLOAD')

    def arb_loaded(self) -> bool:
        return self.command('RAD:ARB:WAV:LOAD?')
