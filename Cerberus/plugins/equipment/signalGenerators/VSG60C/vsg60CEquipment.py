import logging
from typing import Any

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.baseEquipment import Identity
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.visaDevice import VISADevice


@hookimpl
@singleton
def createEquipmentPlugin():
    return VSG60C()


class VSG60C(BaseSigGen):
    def __init__(self):
        super().__init__("VSG60C Signal Generator")
        self.identity: Identity | None
        self.visa: VISADevice

        self._init = {"Port": 5024, "IPAddress": "127.0.0.1"}

    def initialise(self, init: Any | None = None) -> bool:
        if self.initialised:
            return True

        if init is not None:
            super().initialise(init)

        self.visa = VISADevice(self._init["Port"], self._init["IPAddress"])
        if self.visa.open() is None:
            logging.error("Failed to open the VSG60C Signal Generator")
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

########################################################################################################################
# The methods in this section are the basic commands for Cerberus and for the Equipment Shell
########################################################################################################################

    def setOutputPower(self, level_dBm):
        return self.set_power(level_dBm)

########################################################################################################################
# The methods below are the library commands for the signal generator
########################################################################################################################

    def reset(self):
        """Reset the signal generator"""
        cmdString = '*RST'
        logging.debug('Resetting Sig. Gen.')
        self.visa.write(cmdString)

    def trigger(self):
        """Trigger the signal generator"""
        cmdString = '*TRG'
        logging.debug('Triggering Sig. Gen.')
        self.visa.write(cmdString)

    def output_on(self):
        """Turn the output on"""
        cmdString = 'OUTPUT ON'
        logging.debug('Switching ON Sig. Gen. Output')
        self.visa.write(cmdString)

    def output_off(self):
        """Turn the output off"""
        cmdString = 'OUTPUT OFF'
        logging.debug('Switching OFF Sig. Gen. Output')
        self.visa.write(cmdString)

    def Mod_on(self):
        """Turn the modulation on"""
        cmdString = 'OUTPUT:MOD ON'
        logging.debug('Switching ON Sig. Gen. Modulation')
        self.visa.write(cmdString)

    def Mod_off(self):
        """Turn the modulation off"""
        cmdString = 'OUTPUT:MOD OFF'
        logging.debug('Switching OFF Sig. Gen. Modulation')
        self.visa.write(cmdString)

    def set_freq(self, freq):
        """Set the output frequency"""
        freq_sent = f'{freq}MHz'
        cmdString = f'FREQ {freq_sent}'
        logging.debug(f'Setting Signal Frequency to {freq_sent}')
        self.visa.write(cmdString)

    def get_freq(self):
        """Get the output frequency"""
        cmdString = 'FREQ?'
        response = self.visa.query(cmdString)
        logging.debug(response)
        return response

    def set_freq_step(self, freq):
        """Set the frequency step"""
        freq_sent = f'{freq}MHz'
        cmdString = f'FREQ:STEP {freq_sent}'
        logging.debug(f'Setting Signal Frequency Step to {freq_sent}')
        self.visa.write(cmdString)

    def set_power(self, power_lvl):
        """Set the output power level in dBm"""
        power_sent = power_lvl
        cmdString = f'POW {power_sent}'
        logging.debug(f'Setting Signal Power Level to {power_sent}dBm')
        self.visa.write(cmdString)

    def get_power(self):
        """Get the output power level in dBm"""
        cmdString = 'POW?'
        response = self.visa.query(cmdString)
        logging.debug(response)
        return response

    def set_power_step(self, power_step):
        """Set the power step value in dB"""
        power_sent = power_step
        cmdString = f'POW:STEP {power_sent}'
        logging.debug(f'Setting Signal Power Step to {power_sent}dB')
        self.visa.write(cmdString)

    def stream_output(self, bool):
        """"Turns the Signal Generator IQ streaming on/off (Bool)"""
        cmdString = f'STREAMING {bool}'

        if bool == 0:
            logging.debug('Turning IQ Streaming OFF')
        else:
            logging.debug('Turning IQ Streaming ON')

        self.visa.write(cmdString)

    def set_stream_rate(self, freq):
        """
        Sets Streaming Sampling Frequency\n
        Sampling frequency in MHz
        """
        cmdString = f'STREAM:SRAT {freq}MHz'
        logging.debug(f'setting IQ Sampling Frequency: {freq}MHz')
        self.visa.write(cmdString)

    def set_iq_scale(self, scale):
        """
        Sets the scale of the IQ value pairs\n
        Scale veriable as a percentage 0-100
        """
        cmdString = f'STREAM:IQ:SCALE {scale}'
        logging.debug(f'Setting IQ Scale: {scale}')
        self.visa.write(cmdString)

    def load_iq(self, file, type):
        """
        Function loads the IQ Data file to the Signal Generator\n
        file types:'WAV' '16BIT' '32BIT'
        """
        if type not in ['WAV', '16BIT', '32BIT']:
            logging.debug('ERR in file type command\nload_iq function accepts WAV,16BIT,32BIT')
            return

        if type == '16BIT':
            type = 'BINSC'
        if type == '32BIT':
            type = 'BINFC'

        cmdString = f'STREAM:WAV:LOAD:{type} "{file}"'
        logging.debug(f'Loading IQ file: {file}')
        self.visa.write(cmdString)

    def unload_iq(self):
        """
        Function Unloads the IQ data file
        """
        cmdString = 'STREAM:WAV:UNLOAD'
        logging.debug('Unloading IQ file')
        self.visa.write(cmdString)

    def close(self):
        """
        function closes the Signal Generator Connection
        """
        self.rm.close()

    # ARB Commands

    def arb_state(self, bool):
        """
        Function enables ARB output mode"
        """
        cmdString = f'RAD:ARB {bool}'
        logging.debug(f'ARB output mode set to: {bool}')
        self.visa.write(cmdString)

    def arb_load_iq(self, file, type):  # Change this
        """
        Function loads the IQ Data file to the Signal Generator in ARB mode\n
        file types:'WAV' '16BIT' '32BIT'
        """
        if type not in ['WAV', '16BIT', '32BIT']:
            logging.debug('ERR in file type command\nload_iq function accepts WAV,16BIT,32BIT')
            return

        if type == '16BIT':
            type = 'BINSC'
        if type == '32BIT':
            type = 'BINFC'

        cmdString = f'RAD:ARB:WAV:LOAD:{type} "{file}"'
        logging.debug(f'ARB Loading IQ file: {file}')
        self.visa.write(cmdString)

    def arb_mode(self, mode):
        """
        Function sets the mode of the ARB "Single or Continuous"
        """
        cmdString = f'RAD:ARB:TRIG:TYPE {mode}'
        logging.debug(f'Setting Mode of ARB to {mode}')
        self.visa.write(cmdString)

    def arb_sample_rate(self, freq):
        """
        Sets ARB Sampling Frequency\n
        Sampling frequency in MHz
        """
        cmdString = f'RAD:ARB:SRAT {freq}MHz'
        logging.debug(f'Setting ARB IQ Sampling Frequency: {freq}MHz')
        self.visa.write(cmdString)

    def arb_iq_scale(self, scale):
        """
        Sets the scale of the IQ value pairs\n
        Scale veriable as a percentage 0-100
        """
        cmdString = f'RAD:ARB:IQ:SCALE {scale}'
        logging.debug(f'Setting ARB IQ Scale: {scale}')
        self.visa.write(cmdString)

    def arb_auto_scale(self, bool):
        """
        Enables and disabls Auto iq scale\n
        Bool ON || OFF
        """
        cmdString = f'RAD:ARB:IQ:SCALE:AUTO {bool}'
        logging.debug(f'Setting ARB IQ Auto scale to: {bool}')
        self.visa.write(cmdString)

    def arb_unload(self):
        """This function unloads any files that have been loaded into ARB mode"""
        cmdString = 'RAD:ARB:WAV:UNLOAD'
        logging.debug("Unloading files that have been loaded into ARB")
        self.visa.write(cmdString)

    def arb_loaded(self):
        """This function checks to see if a file has been loaded into the sig gen"""
        cmdString = 'RAD:ARB:WAV:LOAD?'
        logging.debug("Checking for file in sig gen")
        query = self.visa.query(cmdString)
        return query
