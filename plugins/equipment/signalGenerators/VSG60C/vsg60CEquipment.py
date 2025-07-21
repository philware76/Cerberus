from plugins import hookimpl, singleton
from plugins.equipment.signalGenerators.baseSigGen import BaseSigGen

@hookimpl
@singleton
def createEquipmentPlugin():
    return VSG60CEquipment()

class VSG60CEquipment(BaseSigGen):
    def __init__(self):
        super().__init__("VSG60C Signal Generator")