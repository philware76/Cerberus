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
        self.ACCEPTED_MODELS = ["NRP-Z24", "Z24", "NRPZ24"]

    def setFrequency(self, frequencyMHz: float) -> bool:
        """Set measurement frequency for sensor on channel 1."""
        logging.debug("%s setting frequency to %s MHz", self.name, frequencyMHz)
        return self._p().command(f"SENS1:POWER:FREQ {frequencyMHz * 1e6}")

    def getPowerReading(self) -> float:
        resp = self._p().query("READ1?")  # channel 1 only
        try:
            return float(resp.strip())
        except ValueError:
            logging.error("%s received non-numeric power response: %r", self.name, resp)
            return float('nan')

    def setSingleMode(self) -> bool:
        ok = True
        ok &= self._p().command("ABOR")
        ok &= self._p().command("INIT1:CONT OFF")
        return ok

    def setContMode(self) -> bool:
        ok = True
        ok &= self._p().command("ABOR")
        ok &= self._p().command("INIT1:CONT ON")
        return ok

    def setConfig(self, continuous: bool = True) -> bool:
        logging.debug("%s applying sensor configuration (continuous=%s)", self.name, continuous)
        ok = True
        ok &= self._p().command("ABOR")
        ok &= self._p().command("SENS1:UNIT DBM")
        ok &= self._p().command("SENS1:FILT:TYPE AUTO")
        ok &= self._p().command("INIT1:CONT ON" if continuous else "INIT1:CONT OFF")
        return ok
