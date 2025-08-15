import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import ModuleType

from Cerberus.plugins.basePlugin import BasePlugin


class PluginDiscovery(dict[str, BasePlugin]):
    def __init__(self, pluginManager, pluginType, folder):
        self.pm = pluginManager
        self.pluginType = pluginType
        self.folder = Path("Cerberus") / Path("plugins") / Path(f"{folder.lower()}")
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
        for root, dirs, _ in os.walk(self.folder):
            dirs[:] = [d for d in dirs if not d.startswith("__") and not d.startswith(".") and not d == "keys" and not d.startswith("nesie")]

            if not dirs:  # This is a leaf folder
                yield root

    def _loadModule(self, moduleName: str, filePath: str) -> ModuleType | None:
        try:
            # If already loaded, return from sys.modules
            if moduleName in sys.modules:
                return sys.modules[moduleName]

            spec = importlib.util.spec_from_file_location(moduleName, filePath)
            if not spec or not spec.loader:
                logging.error(f"Failed to create spec for module: {moduleName}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[moduleName] = module  # ✅ Register with full module name
            spec.loader.exec_module(module)
            return module

        except Exception as e:
            logging.exception(f"Exception loading module {moduleName} from {filePath}: {e}")
            return None

    def _createPlugin(self, pluginName: str, module: ModuleType) -> (BasePlugin | None):
        try:
            self.pm.register(module, name=pluginName)
            createFunc = getattr(module, self.createMethodName)
            basePlugin = createFunc()
            logging.info(f" - Plugin registered: {basePlugin.name}")
            return basePlugin

        except ValueError:
            logging.error(f"Failed to register plugin {pluginName}. Ensure plugins are correctly implemented.")
            return None

    def _registerPlugin(self, pluginName, filePath):
        module = self._loadModule(pluginName, filePath)
        if module is None:
            return

        if hasattr(module, self.createMethodName):
            plugin: BasePlugin | None = self._createPlugin(pluginName, module)
            if plugin is not None:
                self[plugin.name] = plugin
        else:
            pass  # logging.debug(f"Skipped {pluginName}: no '{self.createMethodName}' specification found")

    def __getitem__(self, key: str) -> BasePlugin:
        if key is None or key == "":
            raise ValueError("Empty Plugin name, name must be valid")

        key_lower = key.lower()
        for existing_key in self:
            if isinstance(existing_key, str) and existing_key.lower() == key_lower:
                return super().__getitem__(existing_key)

        raise KeyError(f"Plugin '{key}' not found.")

    def _checkForMissingImplementations(self) -> bool:
        hookCaller = getattr(self.pm.hook, self.createMethodName, None)
        if hookCaller is None:
            logging.error(f"Can't find createPlugin hook {self.createMethodName}")
            return False

        implementations = hookCaller.get_hookimpls()
        if not implementations:
            logging.error(f"No {self.createMethodName} implementations found for {self.pluginType} plugins. Ensure plugins are correctly implemented.")
            return False

        elif len(implementations) != self.registeredPlugins:
            logging.warning(f"Only {len(implementations)} implementations found for {self.registeredPlugins} {self.pluginType} plugins. Ensure plugins are correctly implemented.")
            return False

        return True

    def loadPlugins(self, pluginFolders=None):
        if pluginFolders is None:
            pluginFolders = self._getPluginFolders()

        missingPlugins = []

        for pluginFolder in pluginFolders:
            logging.info(f"Loading {self.pluginType} plugin from: {pluginFolder}")
            pluginCount = 0
            for entry in os.scandir(pluginFolder):
                if entry.is_file() and not entry.name.startswith("__"):
                    if entry.name.endswith(f"{self.pluginType}.py"):
                        abs_plugin_path = os.path.abspath(entry.path)
                        abs_project_root = os.path.abspath(".")  # Or wherever your root is
                        rel_path = os.path.relpath(abs_plugin_path, abs_project_root)
                        module_name = rel_path.replace(os.sep, ".")[:-3]  # remove .py

                        self._registerPlugin(module_name, entry.path)

                        self.registeredPlugins += 1
                        pluginCount += 1
                    else:
                        pass  # logging.debug(f"Skipped {entry.name} - module doesn't end in {self.pluginType}.py")
                else:
                    pass  # logging.debug(f"Skipped {entry.name} - not a valid {self.pluginType}.py plugin file.")

            if pluginCount == 0:
                logging.warning(f"No {self.pluginType} plugins found in {pluginFolder}. Ensure plugins are correctly implemented and named.")
                missingPlugins.append(pluginFolder)

        ImpsOK = self._checkForMissingImplementations()
        if not ImpsOK:
            logging.error("Some hooks are not valid/registered/broken/missing... please check!")

        logging.debug(f"Finished registering {self.pluginType} plugins.")

        return missingPlugins
