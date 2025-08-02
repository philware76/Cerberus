from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.chambers.baseChamber import BaseChamber


@hookimpl
@singleton
def createEquipmentPlugin():
    return NanoDAC()

class NanoDAC(BaseChamber):
    def __init__(self):
        super().__init__("NanoDAC Chamber")