
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.powerMeters.RohdeSchwarz.baseNPRPowerMeter import \
    BaseNRPPowerMeter


@hookimpl
@singleton
def createEquipmentPlugin():
    return NRP_Z24()


class NRP_Z24(BaseNRPPowerMeter):
    def __init__(self):
        super().__init__("NRP-Z24")

    def setFrequency(self, freq: float) -> bool:
        raise NotImplementedError("setFrequency")

    def getPowerReading(self) -> float:
        raise NotImplementedError("getPowerReading")
