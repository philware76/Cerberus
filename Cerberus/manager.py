import logging
from typing import Dict, List, Tuple, Type, cast

import iniconfig
import pluggy

from Cerberus.database import Database, dbInfo
from Cerberus.plan import Plan
from Cerberus.pluginDiscovery import PluginDiscovery
from Cerberus.plugins.basePlugin import BasePlugin
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.equipment.chambers.baseChamber import BaseChamber
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.tests.baseTest import BaseTest


class Manager():
    def __init__(self):
        logging.info("Starting TestManager...")
        self.pm = pluggy.PluginManager("cerberus")

        self.loadIni()
        logging.info(f"Cerberus:{self.stationId}")

        self.database = Database(self.stationId, self.dbInfo)
        self.loadPlan()
        self.loadChamber()

        self.equipPlugins: Dict[str, BaseEquipment] = cast(Dict[str, BaseEquipment], self._discover_plugins("Equipment", "equipment"))
        self.productPlugins: Dict[str, BaseProduct] = cast(Dict[str, BaseProduct], self._discover_plugins("Product", "products"))
        self.testPlugins: Dict[str, BaseTest] = cast(Dict[str, BaseTest], self._discover_plugins("Test", "tests"))

    def loadPlan(self):
        """Load the current test plan for this station from the database."""
        self.plan = self.database.get_TestPlanForStation()

    def savePlan(self):
        """Save the current test plan for this station to the database."""
        if self.plan:
            id = self.database.saveTestPlan(self.plan)
            logging.debug(f"Test plan '{id}' saved successfully.")
        else:
            logging.warning("No test plan to save.")

    def setTestPlan(self, planId: int) -> bool:
        """Set the test plan for this station in the database.
        Returns True if set successfully, False otherwise.
        """
        if not planId:
            logging.error("Test plan ID cannot be empty.")
            return False

        if self.database.set_TestPlanForStation(planId):
            logging.debug(f"Test plan set to: {planId}")
            return True
        else:
            logging.error(f"Failed to set test plan to: {planId}")
            return False
        
    def loadChamber(self):
        """Load the chamber class for this station from the database."""
        self.chamber = self.database.get_ChamberForStation()
        if self.chamber:
            logging.debug(f"Chamber class loaded: {self.chamber}")
        else:
            logging.warning("No chamber class found for this station.")

    def saveChamber(self, chamberName: str) -> bool:
        """Save the chamber class for this station in the database.
        Returns True if set successfully, False otherwise.
        """
        if not chamberName:
            logging.error("Chamber class name cannot be empty.")
            return False

        # Check if chamber_class is a valid BaseChamber subclass
        chamber_plugin = self.findEquipment(chamberName)
        if not chamber_plugin or not isinstance(chamber_plugin, BaseChamber):
            logging.error(f"Chamber class '{chamberName}' is not a valid BaseChamber subclass.")
            return False

        if self.database.set_ChamberForStation(chamberName):
            logging.info(f"Chamber class set to: {chamberName}")
            return True
        else:
            logging.error(f"Failed to set chamber class to: {chamberName}")
            return False

    def loadIni(self):
        ini = iniconfig.IniConfig("cerberus.ini")
        if ini is None:
            logging.error("Failed to load cerberus.ini file!")
            exit(1)

        self.stationId = ini["cerberus"]["identity"]
        self.dbInfo = dbInfo(
            host=ini["database"]["host"],
            username=ini["database"]["username"],
            password=ini["database"]["password"],
            database=ini["database"]["database"]
        )

    def findTest(self, testName: str) -> BaseTest | None:
        """Return a particular test"""
        return self.testPlugins.get(testName, None)

    def findEquipment(self, equipName: str) -> BaseEquipment | None:
        """Return a particular equipment instance"""
        return self.equipPlugins.get(equipName, None)

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
    
    def _discover_plugins(self, pluginType: str, folder: str) -> Dict[str, BasePlugin]:
        plugins = PluginDiscovery(self.pm, pluginType, folder)
        self.missingPlugins = plugins.loadPlugins()

        if len(self.missingPlugins) > 0:
            logging.warning(f"Missing plugins: {self.missingPlugins}")

        return plugins

    def checkRequirements(self, test: BaseTest) -> Tuple[List[BaseEquipment], List[BaseEquipment]]:
        missingEquipmentTypes = []
        foundEquipment = []

        logging.warning(f"Checking requirements for test: {test.name}")
        equipmentRequirements: List[Type[BaseEquipment]] = test.requiredEquipment
        equipmentList = self.equipPlugins.values()

        for equipType in equipmentRequirements:
            logging.debug(" - Required equipment: %s", equipType.__name__)

            # Find all equipment instances matching this required type
            matching_equips = [equip for equip in equipmentList if isinstance(equip, equipType)]

            if matching_equips:
                for equip in matching_equips:
                    logging.debug(f"   - Found: {equip.name}")
                    foundEquipment.append(equip)

            else:
                logging.debug(f"   - Missing: {equipType.__name__}")
                missingEquipmentTypes.append(equipType.__name__)

        return foundEquipment, missingEquipmentTypes

    def getRequirements(self, test: BaseTest) -> dict[str, list[BaseEquipment]]:
        """Return a dict mapping required equipment type names to a list of matching equipment instances."""
        requirement_matches = {}

        logging.warning(f"Checking requirements for test: {test.name}")
        equipmentRequirements: List[Type[BaseEquipment]] = test.requiredEquipment

        for equipType in equipmentRequirements:
            type_name = equipType.__name__
            logging.debug(" - Required equipment: %s", type_name)

            matching_equips = self.findEquipTypes(equipType)

            if matching_equips:
                for equip in matching_equips.values():
                    logging.debug(f"   - Found: {equip.name}")
            else:
                logging.debug(f"   - Missing: {type_name}")

            requirement_matches[type_name] = list(matching_equips.values())

        return requirement_matches
    
    def finalize(self):
        """Final cleanup before exiting the application."""
        logging.debug("Finalizing Cerberus manager...")
        
        # Close the database connection if it exists
        if hasattr(self, 'database') and self.database:
            self.database.close()
            logging.debug("Database connection closed.")
        
        # Any other cleanup tasks can be added here
        logging.debug("Cerberus manager finalized.")