from testManager import TestManager
from cmdShells.common import displayPluginCategory, getInt
from cmdShells.baseShell import BaseShell
from cmdShells.runCommandShell import RunCommandShell
from plugins.equipment.baseEquipment import BaseEquipment

class EquipShell(BaseShell):
    intro = "Welcome to Cerberus Equipment System. Type help or ? to list commands.\n"
    prompt = 'Equipment> '

    def __init__(self, manager: TestManager):
        super().__init__()

        self.manager = manager

    def do_list(self, arg):
        """List all of the Equipment"""
        displayPluginCategory("Equipment", self.manager.equipPlugins)

    def do_load(self, equipName):
        """Loads equipment"""
        try:
            if idx := getInt(equipName):
                equip = self.manager.equipment[idx]
            else:
                equip = self.manager.equipPlugins[equipName]

            EquipmentShell(equip).cmdloop()

        except KeyError:
            print(f"Unknown equipment: {equipName}")

class EquipmentShell(RunCommandShell):
    def __init__(self, equip:BaseEquipment):
        EquipmentShell.intro = f"Welcome to Cerberus {equip.name} Equipment System. Type help or ? to list commands.\n"
        EquipmentShell.prompt = f"{equip.name}> "

        super().__init__(equip)
        self.equip: BaseEquipment = equip
        self.config = {}