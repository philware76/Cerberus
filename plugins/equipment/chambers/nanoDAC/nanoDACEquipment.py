from plugins.basePlugin import hookimpl, singleton
from plugins.equipment.chambers.baseChamber import BaseChamber

@hookimpl
@singleton
def createEquipmentPlugin():
    return NanoDacEquipment()

class NanoDacEquipment(BaseChamber):
    def __init__(self):
        super().__init__("NanoDAC Chamber") 