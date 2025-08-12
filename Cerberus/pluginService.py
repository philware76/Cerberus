import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Dict, List, Tuple, Type, TypeVar, cast

import pluggy

from Cerberus.pluginDiscovery import PluginDiscovery
from Cerberus.plugins.basePlugin import BasePlugin
from Cerberus.plugins.common import PROD_ID_MAPPING
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.tests.baseTest import BaseTest

# Generic type variable for equipment specialisation
T = TypeVar("T", bound=BaseEquipment)


# New unified requirements container
@dataclass
class Requirements:
    # All matching candidates per required equipment type
    candidates: Dict[Type[BaseEquipment], List[BaseEquipment]]
    # Types that have no candidates available
    missing: List[Type[BaseEquipment]]
    # Selected instance per required type based on current policy (not initialised)
    selection: Dict[Type[BaseEquipment], BaseEquipment]


class PluginService:
    def __init__(self):
        self.pm = pluggy.PluginManager("cerberus")
        self.missingPlugins = []

        # Expose as Mapping for covariance; internal structure remains mutable dict from discovery.
        self.equipPlugins: Mapping[str, BaseEquipment] = cast(Dict[str, BaseEquipment], self._discover_plugins("Equipment", "equipment"))
        self.productPlugins: Mapping[str, BaseProduct] = cast(Dict[str, BaseProduct], self._discover_plugins("Product", "products"))
        self.testPlugins: Mapping[str, BaseTest] = cast(Dict[str, BaseTest], self._discover_plugins("Test", "tests"))

        self._checIDkMapping()

    def _checIDkMapping(self):
        for _, prodName in PROD_ID_MAPPING.items():
            if not self.findProduct(prodName):
                logging.warning(f"Failed to find Product '{prodName}' in ProdIDMapping dictionary.")

    def findTest(self, testName: str) -> BaseTest | None:
        """Return a particular test"""
        return self.testPlugins.get(testName, None)

    def findEquipment(self, equipName: str) -> BaseEquipment | None:
        """Return a particular equipment instance"""
        return self.equipPlugins.get(equipName, None)

    def findEquipType(self, name: str, expected_type: Type[T]) -> T | None:
        equip = self.equipPlugins.get(name, None)
        if equip is None:
            return None

        if isinstance(equip, expected_type):
            return cast(T, equip)

        logging.debug(f"Equipment '{name}' is not of expected type '{expected_type.__name__}'")
        return None

    def findEquipTypes(self, classType) -> dict:
        """Return a dictionary of {name: instance} for equipment matching the given class type."""
        return {
            name: plugin for name, plugin in self.equipPlugins.items()
            if isinstance(plugin, classType)
        }

    def findProduct(self, productName: str) -> BaseProduct | None:
        return self.productPlugins.get(productName, None)

    def findProductTypes(self, classType) -> dict:
        """Return a dictionary of {name: instance} for products matching the given class type."""
        return {
            name: plugin for name, plugin in self.productPlugins.items()
            if isinstance(plugin, classType)
        }

    def _discover_plugins(self, pluginType: str, folder: str) -> Dict[str, BasePlugin]:  # returns a mutable dict internally
        plugins = PluginDiscovery(self.pm, pluginType, folder)
        self.missingPlugins = plugins.loadPlugins()

        if len(self.missingPlugins) > 0:
            logging.warning(f"Missing plugins: {self.missingPlugins}")

        return plugins

    # Deprecated: now delegates to getRequirements to preserve compatibility
    def checkRequirements(self, test: BaseTest) -> Tuple[Dict[Type[BaseEquipment], List[BaseEquipment]], List[str]]:
        """Return a mapping of required types to available equipment instances (not initialised), and a list of missing type names."""
        reqs = self.getRequirements(test)
        missing_names = [t.__name__ for t in reqs.missing]
        return reqs.candidates, missing_names

    # New unified API: compute candidates, missing, and a selection in one call
    def getRequirements(self, test: BaseTest) -> Requirements:
        """Return requirements info: candidates per type, missing types, and a selected instance per required type (not initialised)."""
        candidates: Dict[Type[BaseEquipment], List[BaseEquipment]] = {}
        missing: List[Type[BaseEquipment]] = []
        selection: Dict[Type[BaseEquipment], BaseEquipment] = {}

        logging.warning(f"Checking requirements for test: {test.name}")
        equipmentRequirements: List[Type[BaseEquipment]] = test.requiredEquipment
        equipmentList = list(self.equipPlugins.values())

        for equipType in equipmentRequirements:
            logging.debug(" - Required equipment: %s", equipType.__name__)
            matches = [equip for equip in equipmentList if isinstance(equip, equipType)]
            if matches:
                candidates[equipType] = matches
                for equip in matches:
                    logging.debug(f"   - Found: {equip.name}")
                # Selection policy: first candidate
                selection[equipType] = matches[0]
            else:
                logging.debug(f"   - Missing: {equipType.__name__}")
                missing.append(equipType)

        return Requirements(candidates=candidates, missing=missing, selection=selection)

    # Deprecated: now delegates to getRequirements to preserve compatibility
    def selectEquipmentFor(self, test: BaseTest) -> Dict[Type[BaseEquipment], BaseEquipment]:
        """Choose one equipment instance per required type for the given test (no initialisation).
        Current policy: pick the first available candidate for each required type.
        """
        return self.getRequirements(test).selection
