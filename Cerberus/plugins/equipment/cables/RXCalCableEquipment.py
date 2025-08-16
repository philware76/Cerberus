from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.cables.baseCalCable import BaseCalCable


@hookimpl
@singleton
def createEquipmentPlugin():
    return RXCalCable()


class RXCalCable(BaseCalCable):
    def __init__(self):
        super().__init__("RX")
