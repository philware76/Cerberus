import importlib.util
import os
from pathlib import Path

class PluginDiscovery:
    def __init__(self, pluginManager, pluginType, folder):
        self.pm = pluginManager
        self.pluginType = pluginType
        self.folder = Path("plugins") / Path(f"{folder.lower()}")

        # Dynamically import hookspec class based on pluginType
        # Replace os.sep with "." to convert a filesystem path to a Python module import path.
        # For example, "plugins/tests/myTestPlugin" becomes "plugins.tests.myTestPlugin".
        hookspec_module = importlib.import_module(str(self.folder).replace(os.sep, ".") + ".hookspecs")
        hookspec_class_name = f"{pluginType}Spec"
        hookspec_class = getattr(hookspec_module, hookspec_class_name)
        self.pm.add_hookspecs(hookspec_class)

    def _getPluginFolders(self):
        print(f"[Cerberus] Looking for {self.pluginType} Plugins in:", self.folder)
        pluginFolders = [
            entry.name
            for entry in os.scandir(self.folder)
                if entry.is_dir() and not entry.name.startswith("__")
        ]
        for pluginFolder in pluginFolders:
            yield os.path.join(self.folder, pluginFolder)

    def _registerPlugin(self, pluginName, plugin_file_path):
        spec = importlib.util.spec_from_file_location(pluginName, plugin_file_path)
        module = importlib.util.module_from_spec(spec)
    
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"[Cerberus] Failed to load plugin {plugin_file_path}: {e}")
            return
        
        if hasattr(module, createMethodName := f"create{self.pluginType}Plugin"):
            self.pm.register(module, name=pluginName)
            print(f"[Cerberus] Plugin registered: {pluginName}")
        else:
            print(f"[Cerberus] Skipped {plugin_file_path}: no '{createMethodName}' method found")

    def loadPlugins(self, pluginFolders=None):
        if pluginFolders is None:
            pluginFolders = self._getPluginFolders()
        
        for pluginFolder in pluginFolders:
            print(f"[Cerberus] Loading {self.pluginType} plugin from: {pluginFolder}")
            for entry in os.scandir(pluginFolder):
                if entry.is_file() and entry.name.endswith(f"{self.pluginType}.py") and not entry.name.startswith("__"):
                    self._registerPlugin(entry.name[:-3], entry.path)