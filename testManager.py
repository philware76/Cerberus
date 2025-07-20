from pdb import pm
from typing import List
import pluggy

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

