
import logging

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.powerMeters.RohdeSchwarz.NRP.baseNRPPowerMeter import \
    BaseNRPPowerMeter


@hookimpl
@singleton
def createEquipmentPlugin():
    return NRP_Z22()


class NRP_Z22(BaseNRPPowerMeter):
    def __init__(self):
        super().__init__("NRP-Z22")
        self.ACCEPTED_MODELS = ["NRP-Z22", "Z22", "NRPZ22"]
        self.excluded = False

    def setFrequency(self, frequencyMHz: float) -> bool:
        logging.debug("%s setting frequency to %s MHz", self.name, frequencyMHz)
        return self._p().command(f"SENSe:FREQuency {frequencyMHz * 1e6}")

    def getPowerReading(self) -> float:
        resp = self._p().query("READ?")
        try:
            return float(resp.strip())
        except ValueError:
            logging.error("%s received non-numeric power response: %r", self.name, resp)
            return float('nan')
