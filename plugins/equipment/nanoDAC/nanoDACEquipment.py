from plugins import hookimpl
from plugins.equipment.baseChamber import BaseChamber

@hookimpl
def createEquipmentPlugin():
    return NanoDacEquipment()

class NanoDacEquipment(BaseChamber):
    def __init__(self):
        super().__init__("NanoDAC Chamber") 