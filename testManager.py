from pdb import pm
from typing import List
import pluggy
import logging

from pluginDiscovery import PluginDiscovery
from plugins.equipment.baseEquipment import BaseEquipment
from plugins.tests.baseTest import BaseTest

class TestManager:
    def __init__(self):
        self.pm = pluggy.PluginManager("cerberus")
        
        # Test Plugins
        self.Test = PluginDiscovery(self.pm, "Test", "tests")
        self.Test.loadPlugins()
 
        # Equipment Plugins
        self.Equipement = PluginDiscovery(self.pm, "Equipment", "equipment")
        self.Equipement.loadPlugins()

    def checkRequirements(self, test: BaseTest) -> List[BaseEquipment]:
        foundAll = True
        available_equipment = list(self.Equipement.createPlugins())  # list of equipment instances

        for req_type in test.RequiredEquipment:
            logging.debug("Checking for required equipment type: " + req_type.__name__)
            # Find all equipment instances matching this required type
            matching_equips = [equip for equip in available_equipment if isinstance(equip, req_type)]

            if matching_equips:
                for equip in matching_equips:
                    logging.debug(f"Required equipment found: {equip.name}")
            else:
                logging.warning(f"Missing required equipment of type: {req_type.__name__}")
                foundAll = False
        
        return foundAll
