from plugins.basePlugin import hookimpl, singleton
from plugins.equipment.chambers.baseChamber import BaseChamber

@hookimpl
@singleton
def createEquipmentPlugin():
    return CT200Equipment()

class CT200Equipment(BaseChamber):
    def __init__(self):
        super().__init__("CT200 Chamber") 