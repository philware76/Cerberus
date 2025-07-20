# cerberus/testmanager.py
import pluggy
from pluginDiscovery import PluginDiscovery

class TestManager:
    def __init__(self):
        self.pm = pluggy.PluginManager("cerberus")
        
        # Test Plugins
        self.testDiscovery = PluginDiscovery(self.pm, "Test", "tests")
        self.testDiscovery.loadPlugins()
 
    def get_plugin(self, plugin_name):
        return self.pm.get_plugin(plugin_name)

if __name__ == "__main__":
    manager = TestManager()

    plugin = manager.get_plugin("OCXOCalibrationTest")
    if plugin:
        print(f"Found plugin: {plugin.__name__}")
    else:
        print("Plugin not found.")

    test = plugin.createTestPlugin()
    print(f"Created test plugin: {test}")
