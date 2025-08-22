
import logging

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.powerMeters.RohdeSchwarz.NRP.baseNRPPowerMeter import \
    BaseNRPPowerMeter


@hookimpl
@singleton
def createEquipmentPlugin():
    return NRP_Z24()


class NRP_Z24(BaseNRPPowerMeter):
    def __init__(self):
        super().__init__("NRP-Z24")

        self.excluded = False

    def setFrequency(self, frequencyMHz: float) -> bool:
        """Set measurement frequency for sensor on channel 1.

        Always uses channel-qualified form as only SENS1 is supported in this
        deployment.
        """
        logging.debug("%s setting frequency to %s", self.name, freq)
        # Script version used: SENS{ch}:POWER:FREQ <Hz>; align with that (AVER variant may not update).
        return self.command(f"SENS1:POWER:FREQ {freq * 1e6}")

    def getPowerReading(self) -> float:
        resp = self.query("READ1?")  # channel 1 only
        try:
            return float(resp.strip())

        except ValueError:
            logging.error("%s received non-numeric power response: %r", self.name, resp)
            return float('nan')

    # --- Added convenience measurement/mode helpers (auto-exposed in shell) ---
    def setSingleMode(self) -> bool:
        """Configure sensor channel 1 for single-shot measurements.

        Sequence:
            ABOR; INIT1:CONT OFF
        """
        ok = True
        ok &= self.command("ABOR")  # correct SCPI spelling
        ok &= self.command("INIT1:CONT OFF")
        return ok

    def setContMode(self) -> bool:
        """Configure sensor channel 1 for continuous acquisition (FETCh1? loop)."""
        ok = True
        ok &= self.command("ABOR")
        ok &= self.command("INIT1:CONT ON")
        return ok

    def setConfig(self, continuous: bool = True) -> bool:
        """Full sensor configuration similar to working standalone script.

        Performs (all channel 1):
            ABOR
            SENS1:UNIT DBM
            SENS1:FILT:TYPE AUTO
            INIT1:CONT {ON|OFF}

        Args:
            continuous: If True enables continuous mode (FETCh1? for async polling).
        """
        logging.debug("%s applying sensor configuration (continuous=%s)", self.name, continuous)
        ok = True
        ok &= self.command("ABOR")
        ok &= self.command("SENS1:UNIT DBM")
        ok &= self.command("SENS1:FILT:TYPE AUTO")
        ok &= self.command("INIT1:CONT ON" if continuous else "INIT1:CONT OFF")

        return ok
