from cmdShells.pluginsShell import PluginsShell
from testManager import TestManager
from cmdShells.common import displayPluginCategory, getInt
from cmdShells.baseShell import BaseShell
from cmdShells.runCommandShell import RunCommandShell
from plugins.equipment.baseEquipment import BaseEquipment

class EquipShell(PluginsShell):
    def __init__(self, manager:TestManager):
        super().__init__(manager, manager.equipPlugins, "Equipment")

    # def __init__(self, manager: TestManager):
    #     super().__init__()

    #     self.manager = manager

    # def do_list(self, arg):
    #     """List all of the Equipment"""
    #     displayPluginCategory("Equipment", self.manager.equipPlugins)

    # def do_load(self, name):
    #     """Loads equipment"""
    #     try:
    #         if idx := getInt(name):
    #             name = list(self.manager.equipPlugins.keys())[idx]
            
    #         equip = self.manager.equipPlugins[name]

    #         EquipmentShell(equip).cmdloop()

    #     except KeyError:
    #         print(f"Unknown equipment: {name}")

class EquipmentShell(RunCommandShell):
    def __init__(self, equip:BaseEquipment, manager: TestManager):
        EquipmentShell.intro = f"Welcome to Cerberus {equip.name} Equipment System. Type help or ? to list commands.\n"
        EquipmentShell.prompt = f"{equip.name}> "

        super().__init__(equip, manager)
        self.equip: BaseEquipment = equip
        self.config = {}