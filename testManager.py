# cerberus/testmanager.py
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
        self.testDiscovery = PluginDiscovery(self.pm, "Test", "tests")
        self.testDiscovery.loadPlugins()
 
        # Equipment Plugins
        self.equipmentDiscovery = PluginDiscovery(self.pm, "Equipment", "equipment")
        self.equipmentDiscovery.loadPlugins()

    def get_plugin(self, plugin_name):
        return self.pm.get_plugin(plugin_name)
    
    def createTestPlugins(self) -> List[BaseTest]:
        return self.pm.hook.createTestPlugin()
    
    def createEquipmentPlugins(self) -> List[BaseEquipment]:
        return self.pm.hook.createEquipmentPlugin()


logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] [%(module)s] %(message)s')

if __name__ == "__main__":
    manager = TestManager()

    logging.info("Available equipment plugins:")
    for equipment in manager.createEquipmentPlugins():
        logging.info(" - " + equipment.name)

    logging.info("Available test plugins:")
    for test in manager.createTestPlugins():
        logging.info(" - " + test.name)

    plugin = manager.get_plugin("txLevelTest")
    if plugin:
        print(f"Found plugin: {plugin.__name__}")
    else:
        print("Plugin not found.")

    test = plugin.createTestPlugin()
    print(f"Created test plugin: {test}")

    test.run()
    result = test.getResult()
    logging.info(f"Test result: {result.name} - {result.status}")