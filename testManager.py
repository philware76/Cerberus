from typing import Any, Dict, List, Mapping, Tuple, Type, cast
import pluggy
import logging

from pluginDiscovery import PluginDiscovery
from plugins.basePlugin import BasePlugin
from plugins.equipment.baseEquipment import BaseEquipment
from plugins.products.baseProduct import BaseProduct
from plugins.tests.baseTest import BaseTest


class TestManager:
    def __init__(self):
        logging.info("Starting TestManager...")
        self.pm = pluggy.PluginManager("cerberus")

        self.equipPlugins: Dict[str, BaseEquipment] = cast(Dict[str, BaseEquipment], self._discover_plugins("Equipment", "equipment"))
        self.productPlugins: Dict[str, BaseProduct] = cast(Dict[str, BaseProduct], self._discover_plugins("Product", "products"))
        self.testPlugins: Dict[str, BaseTest] = cast(Dict[str, BaseTest], self._discover_plugins("Test", "tests"))

        self.equipment: List[BaseEquipment] = list(self.equipPlugins.values())
        self.products: List[BaseProduct] = list(self.productPlugins.values())
        self.tests: List[BaseTest] = list(self.testPlugins.values())

    def _discover_plugins(self, pluginType: str, folder: str) -> Dict[str, BasePlugin]:
        plugins = PluginDiscovery(self.pm, pluginType, folder)
        plugins.loadPlugins()
        return plugins

    def checkRequirements(self, test: BaseTest) -> Tuple[bool, List[BaseEquipment]]:
        foundAll = True
        missingEquipment = []

        logging.debug(f"Checking requirements for test: {test.name}")
        equipmentRequirements: List[Type[BaseEquipment]] = test.RequiredEquipment
        for equipment in equipmentRequirements:
            logging.debug(" - Required equipment: " + equipment.__name__)
            # Find all equipment instances matching this required type
            matching_equips = [equip for equip in self.equipment if isinstance(equip, equipment)]

            if matching_equips:
                for equip in matching_equips:
                    logging.debug(f"   - Found: {equip.name}")
            else:
                logging.warning(f"   - Missing: {equipment.__name__}")
                missingEquipment.append(equipment.__name__)
                foundAll = False

        return foundAll, missingEquipment
