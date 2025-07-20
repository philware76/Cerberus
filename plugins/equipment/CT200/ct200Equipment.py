from plugins import hookimpl
from plugins.equipment.baseChamber import BaseChamber

@hookimpl
def createEquipmentPlugin():
    return CT200Equipment()

class CT200Equipment(BaseChamber):
    def __init__(self):
        super().__init__("CT200 Chamber") 