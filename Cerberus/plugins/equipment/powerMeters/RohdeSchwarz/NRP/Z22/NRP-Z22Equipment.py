
import logging

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.powerMeters.RohdeSchwarz.NRP.baseNPRPowerMeter import \
    BaseNRPPowerMeter


@hookimpl
@singleton
def createEquipmentPlugin():
    return NRP_Z22()


class NRP_Z22(BaseNRPPowerMeter):
    def __init__(self):
        super().__init__("NRP-Z22")

    def setFrequency(self, freq: float) -> bool:
        # Placeholder SCPI command; adjust to actual sensor command set
        # Delegated through parent (SMB100A) connection
        logging.debug("%s setting frequency to %s", self.name, freq)
        return self.command(f"SENSe:FREQuency {freq}")

    def getPowerReading(self) -> float:
        # Placeholder; real implementation should parse sensor specific response
        resp = self.query("READ?")
        try:
            return float(resp.strip())
        except ValueError:
            logging.error("%s received non-numeric power response: %r", self.name, resp)
            return float('nan')
