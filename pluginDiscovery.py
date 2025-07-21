import importlib.util
import logging
import os
from pathlib import Path
from typing import List

from plugins.basePlugin import BasePlugin

class PluginDiscovery:
    def __init__(self, pluginManager, pluginType, folder):
        self.pm = pluginManager
        self.pluginType = pluginType
        self.folder = Path("plugins") / Path(f"{folder.lower()}")
        self.registeredPlugins = 0
        self._createPlugins = {}

        # Dynamically import hookspec class based on pluginType
        # Replace os.sep with "." to convert a filesystem path to a Python module import path.
        # For example, "plugins/tests/myTestPlugin" becomes "plugins.tests.myTestPlugin".
        hookspec_module = importlib.import_module(str(self.folder).replace(os.sep, ".") + ".hookspecs")
        hookspec_class_name = f"{pluginType}Spec"
        hookspec_class = getattr(hookspec_module, hookspec_class_name)
        self.pm.add_hookspecs(hookspec_class)

        self.createMethodName = f"create{self.pluginType}Plugin"

        logging.info(f"Discovering {self.pluginType} plugins in {self.folder}")

    def _getPluginFolders(self):
        for root, dirs, files in os.walk(self.folder):
            dirs[:] = [d for d in dirs if not d.startswith("__") and not d.startswith(".")]

            if not dirs:  # This is a leaf folder
                yield root

    def _registerPlugin(self, pluginName, plugin_file_path):
        spec = importlib.util.spec_from_file_location(pluginName, plugin_file_path)
        module = importlib.util.module_from_spec(spec)
    
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logging.error(f"Failed to load plugin {plugin_file_path}: {e}")
            return
        
        if hasattr(module, self.createMethodName):
            try:
                self.pm.register(module, name=pluginName)
                self._createPlugins[pluginName] = getattr(module, self.createMethodName)
                logging.info(f" - Plugin registered: {pluginName}")
            except ValueError as e:
                logging.error(f"Failed to register plugin {pluginName}. Ensure plugins are correctly implemented.")
        else:
            logging.debug(f"Skipped {plugin_file_path}: no '{self.createMethodName}' specification found")

    def listPlugins(self) -> List[BasePlugin]:
       return list(self._createPlugins.keys())
    
    def getPlugin(self, pluginName) -> BasePlugin:
        for name in self._createPlugins:
            if name.lower() == pluginName.lower():
                return self._createPlugins[name]()

        logging.error(f"Plugin {pluginName} not found.")
        return None

    # Create all the plugins based on the registered methods
    def createPlugins(self) -> List[BasePlugin]:
        return [func() for func in self._createPlugins.values()]

    def _checkForMissingImplementations(self):
        hookCaller = getattr(self.pm.hook, self.createMethodName, None)        
        implementations = hookCaller.get_hookimpls()
        if not implementations:
            logging.error(f"No {self.createMethodName} implementations found for {self.pluginType} plugins. Ensure plugins are correctly implemented.")

        elif len(implementations) != self.registeredPlugins:
            logging.warning(f"Only {len(implementations)} implementations found for {self.registeredPlugins} {self.pluginType} plugins. Ensure plugins are correctly implemented.")

    def loadPlugins(self, pluginFolders=None):
        if pluginFolders is None:
            pluginFolders = self._getPluginFolders()
        
        for pluginFolder in pluginFolders:
            logging.info(f"Loading {self.pluginType} plugin from: {pluginFolder}")
            pluginCount = 0
            for entry in os.scandir(pluginFolder):
                if entry.is_file() and entry.name.endswith(f"{self.pluginType}.py") and not entry.name.startswith("__"):
                    self._registerPlugin(entry.name[:-3], entry.path)
                    self.registeredPlugins += 1
                    pluginCount += 1
                else:
                    logging.trace(f"Skipped {entry.name} - not a valid {self.pluginType} plugin file.")
            
            if pluginCount == 0:
                logging.warning(f"No {self.pluginType} plugins found in {pluginFolder}. Ensure plugins are correctly implemented and named.")


        if self.registeredPlugins > 0:
            self._checkForMissingImplementations()
        else:   
            logging.warning(f"No {self.pluginType} plugins found in {self.folder}. Ensure plugins are correctly implemented and named.")

        logging.debug(f"Finished registering {self.pluginType} plugins.")