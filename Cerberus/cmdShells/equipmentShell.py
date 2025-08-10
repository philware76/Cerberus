from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.manager import Manager
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment


class EquipShell(PluginsShell):
    def __init__(self, manager: Manager):
        pluginService = manager.pluginService
        super().__init__(manager, pluginService.equipPlugins, "Equipment")


class EquipmentShell(RunCommandShell):
    def __init__(self, equip: BaseEquipment, manager: Manager):
        EquipmentShell.intro = f"Welcome to Cerberus {equip.name} Equipment System. Type help or ? to list commands.\n"
        EquipmentShell.prompt = f"{equip.name}> "

        super().__init__(equip, manager)
        self.equip: BaseEquipment = equip
        self.config = {}
