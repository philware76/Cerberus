from typing import List, Tuple, Generator, Type
import pluggy
import logging

from pluginDiscovery import PluginDiscovery
from plugins.equipment.baseEquipment import BaseEquipment
from plugins.products.baseProduct import BaseProduct
from plugins.tests.baseTest import BaseTest

class TestManager:
    def __init__(self):
        logging.info("Starting TestManager...")
        self.pm = pluggy.PluginManager("cerberus")

        self._equipPlugins    = self._discover_plugins("Equipment", "equipment")
        self._productsPlugins = self._discover_plugins("Product",   "products")
        self._testPlugins     = self._discover_plugins("Test",      "tests")

    def _discover_plugins(self, pluginType: str, folder: str):
        plugins = PluginDiscovery(self.pm, pluginType, folder)
        plugins.loadPlugins()
        return plugins
    
    def equipment(self) -> Generator[BaseEquipment, None, None]:
        yield from self._equipPlugins.values()

    def products(self) -> Generator[BaseProduct, None, None]:
        yield from self._productsPlugins.values()

    def tests(self) -> Generator[BaseTest, None, None]:
        yield from self._testPlugins.values()

    def checkRequirements(self, test: BaseTest) -> Tuple[bool, List[BaseEquipment]]:
        foundAll = True
        missingEquipment = []

        logging.debug(f"Checking requirements for test: {test.name}")
        equipmentRequirements: List[Type[BaseEquipment]] = test.RequiredEquipment
        for equipment in equipmentRequirements:
            logging.debug(" - Required equipment: " + equipment.__name__)
            # Find all equipment instances matching this required type
            matching_equips = [equip for equip in self.equipment() if isinstance(equip, equipment)]

            if matching_equips:
                for equip in matching_equips:
                    logging.debug(f"   - Found: {equip.name}")
            else:
                logging.warning(f"   - Missing: {equipment.__name__}")
                missingEquipment.append(equipment)
                foundAll = False
        
        return foundAll, missingEquipment
