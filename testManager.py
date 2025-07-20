# cerberus/testmanager.py
from pdb import pm
import sys
import trace
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

TRACE_LEVEL_NUM = 5

def setup_logging(level=logging.DEBUG):
    def trace(self, message, *args, **kwargs):
        if self.isEnabledFor(TRACE_LEVEL_NUM):
            self._log(TRACE_LEVEL_NUM, message, args, **kwargs)
    logging.Logger.trace = trace

    def trace_global(message, *args, **kwargs):
        logging.log(TRACE_LEVEL_NUM, message, *args, **kwargs)
    logging.trace = trace_global

    # --- Color formatter ---
    class ColorFormatter(logging.Formatter):
        COLORS = {
            TRACE_LEVEL_NUM: "\033[90m",    # Grey
            logging.DEBUG: "\033[38;5;244m",      # White
            logging.INFO: "\033[32m",       # Green
            logging.WARNING: "\033[33m",    # Yellow
            logging.ERROR: "\033[31m",      # Red
            logging.CRITICAL: "\033[41m",   # Red background
        }
        RESET = "\033[0m"

        def format(self, record):
            color = self.COLORS.get(record.levelno, self.RESET)
            message = super().format(record)
            return f"{color}{message}{self.RESET}"

    formatter = ColorFormatter("[%(levelname)s] [%(module)s:%(lineno)d] %(message)s")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # --- Configure root logger ---
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

if __name__ == "__main__":
    logging.TRACE = TRACE_LEVEL_NUM  # Optional convenience
    logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")

    setup_logging(logging.DEBUG)

    logging.info("Starting TestManager...")
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