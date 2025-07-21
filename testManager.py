from pdb import pm
from typing import List, Tuple
import pluggy
import logging

from pluginDiscovery import PluginDiscovery
from plugins.equipment.baseEquipment import BaseEquipment
from plugins.tests.baseTest import BaseTest

class TestManager:
    def __init__(self):
        logging.info("Starting TestManager...")
        self.pm = pluggy.PluginManager("cerberus")

        self.discoverTestPlugins()
        self.discoverEquipmentPlugins()
        self.discoverProductPlugins()

    def discoverEquipmentPlugins(self):
        self.EquipPlugins = PluginDiscovery(self.pm, "Equipment", "equipment")
        self.EquipPlugins.loadPlugins()
        self.Equipment = list(self.EquipPlugins.createPlugins())

    def discoverProductPlugins(self):
        self.ProductPlugins = PluginDiscovery(self.pm, "Product", "products")
        self.ProductPlugins.loadPlugins()
        self.Products = list(self.ProductPlugins.createPlugins())

    def discoverTestPlugins(self):
        self.TestPlugins = PluginDiscovery(self.pm, "Test", "tests")
        self.TestPlugins.loadPlugins()
        self.Tests = list(self.TestPlugins.createPlugins())

    def checkRequirements(self, test: BaseTest) -> Tuple[bool, List[BaseEquipment]]:
        foundAll = True
        missingEquipment = []
        for req_type in test.RequiredEquipment:
            logging.debug("Checking for required equipment type: " + req_type.__name__)
            # Find all equipment instances matching this required type
            matching_equips = [equip for equip in self.Equipment if isinstance(equip, req_type)]

            if matching_equips:
                for equip in matching_equips:
                    logging.debug(f"Required equipment found: {equip.name}")
            else:
                logging.warning(f"Missing required equipment of type: {req_type.__name__}")
                missingEquipment.append(req_type)
                foundAll = False
        
        return foundAll, missingEquipment
