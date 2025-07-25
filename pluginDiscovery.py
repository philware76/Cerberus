import importlib.util
import logging
import os
from pathlib import Path
from types import ModuleType
from typing import Dict

from plugins.basePlugin import BasePlugin


class PluginDiscovery(Dict[str, BasePlugin]):
    def __init__(self, pluginManager, pluginType, folder):
        self.pm = pluginManager
        self.pluginType = pluginType
        self.folder = Path("plugins") / Path(f"{folder.lower()}")
        self.registeredPlugins = 0

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

    def _loadModule(self, pluginName: str, filePath: str) -> (ModuleType | None):
        spec = importlib.util.spec_from_file_location(pluginName, filePath)
        if spec is None:
            logging.error(f"Can't find spec from file: {filePath}")
            return None

        module = importlib.util.module_from_spec(spec)
        if module is None:
            logging.error(f"Cant find module from spec: {spec}")
            return None

        if spec.loader is None:
            logging.error(f"No loader associated with spec: {spec}")
            return None

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logging.error(f"Failed to load plugin {filePath}: {e}")
            return None

        return module

    def _createPlugin(self, pluginName: str, module: ModuleType) -> (BasePlugin | None):
        try:
            self.pm.register(module, name=pluginName)
            createFunc = getattr(module, self.createMethodName)
            basePlugin = createFunc()
            logging.info(f" - Plugin registered: {basePlugin.name}")
            return basePlugin

        except ValueError as e:
            logging.error(f"Failed to register plugin {pluginName}. Ensure plugins are correctly implemented.")
            return None

    def _registerPlugin(self, pluginName, filePath):
        module = self._loadModule(pluginName, filePath)
        if module is None:
            return

        if hasattr(module, self.createMethodName):
            plugin:BasePlugin = self._createPlugin(pluginName, module)
            if plugin is not None:
                self[plugin.name] = plugin
        else:
            logging.debug(f"Skipped {pluginName}: no '{self.createMethodName}' specification found")

    def __getitem__(self, key: str) -> BasePlugin:
        key_lower = key.lower()
        for existing_key in self:
            if isinstance(existing_key, str) and existing_key.lower() == key_lower:
                return super().__getitem__(existing_key)

        logging.error(f"Plugin {key} not found.")
        raise KeyError(key)

    def _checkForMissingImplementations(self):
        hookCaller = getattr(self.pm.hook, self.createMethodName, None)
        if hookCaller is None:
            logging.error(f"Can't find createPlugin hook {self.createMethodName}")
            return

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
