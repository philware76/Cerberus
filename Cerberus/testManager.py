import logging
from typing import Dict, List, Tuple, Type, cast

import pluggy

from Cerberus.pluginDiscovery import PluginDiscovery
from Cerberus.plugins.basePlugin import BasePlugin
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.tests.baseTest import BaseTest


class TestManager:
    def __init__(self):
        logging.info("Starting TestManager...")
        self.pm = pluggy.PluginManager("cerberus")

        self.equipPlugins: Dict[str, BaseEquipment] = cast(Dict[str, BaseEquipment], self._discover_plugins("Equipment", "equipment"))
        self.productPlugins: Dict[str, BaseProduct] = cast(Dict[str, BaseProduct], self._discover_plugins("Product", "products"))
        self.testPlugins: Dict[str, BaseTest] = cast(Dict[str, BaseTest], self._discover_plugins("Test", "tests"))

    def findTest(self, testName: str) -> BaseTest | None:
        return self.testPlugins.get(testName, None)

    def findEquipment(self, equipName: str) -> BaseEquipment | None:
        return self.equipPlugins.get(equipName, None)

    def findProduct(self, productName: str) -> BaseProduct | None:
        return self.productPlugins.get(productName, None)

    def _discover_plugins(self, pluginType: str, folder: str) -> Dict[str, BasePlugin]:
        plugins = PluginDiscovery(self.pm, pluginType, folder)
        self.missingPlugins = plugins.loadPlugins()

        if len(self.missingPlugins) > 0:
            logging.warning(f"Missing plugins: {self.missingPlugins}")

        return plugins

    def checkRequirements(self, test: BaseTest) -> Tuple[bool, List[BaseEquipment]]:
        foundAll = True
        missingEquipment = []

        logging.warning(f"Checking requirements for test: {test.name}")
        equipmentRequirements: List[Type[BaseEquipment]] = test.requiredEquipment
        equipmentList = self.equipPlugins.values()

        for equipment in equipmentRequirements:
            logging.debug(" - Required equipment: %s", equipment.__name__)

            # Find all equipment instances matching this required type
            matching_equips = [equip for equip in equipmentList if isinstance(equip, equipment)]

            if matching_equips:
                for equip in matching_equips:
                    logging.debug(f"   - Found: {equip.name}")

            else:
                logging.debug(f"   - Missing: {equipment.__name__}")
                missingEquipment.append(equipment.__name__)
                foundAll = False

        return foundAll, missingEquipment
