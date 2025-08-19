
import logging

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.powerMeters.RohdeSchwarz.NRP.baseNPRPowerMeter import \
    BaseNRPPowerMeter


@hookimpl
@singleton
def createEquipmentPlugin():
    return NRP_Z24()


class NRP_Z24(BaseNRPPowerMeter):
    def __init__(self):
        super().__init__("NRP-Z24")

    def setFrequency(self, freq: float) -> bool:
        logging.debug("%s setting frequency to %s", self.name, freq)
        return self.command(f"SENSe:FREQuency {freq}")

    def getPowerReading(self) -> float:
        resp = self.query("READ?")
        try:
            return float(resp.strip())
        except ValueError:
            logging.error("%s received non-numeric power response: %r", self.name, resp)
            return float('nan')
