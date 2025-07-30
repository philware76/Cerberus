from Cerberus.cerberusManager import CerberusManager
from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment


class EquipShell(PluginsShell):
    def __init__(self, manager:CerberusManager):
        super().__init__(manager, manager.equipPlugins, "Equipment")


class EquipmentShell(RunCommandShell):
    def __init__(self, equip:BaseEquipment, manager: CerberusManager):
        EquipmentShell.intro = f"Welcome to Cerberus {equip.name} Equipment System. Type help or ? to list commands.\n"
        EquipmentShell.prompt = f"{equip.name}> "

        super().__init__(equip, manager)
        self.equip: BaseEquipment = equip
        self.config = {}
