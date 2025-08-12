from collections.abc import Mapping
from importlib import import_module

from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.cmdShells.common import displayPluginCategory, getInt
from Cerberus.manager import Manager
from Cerberus.plugins.basePlugin import BasePlugin


class PluginsShell(BaseShell):
    """A base shell class for interacting with plugin dictionaries."""

    def __init__(self, manager: Manager, plugins: Mapping[str, BasePlugin], plugin_type: str):
        super().__init__(manager)
        self.pluginService = manager.pluginService

        PluginsShell.intro = f"Welcome to Cerberus {plugin_type} System. Type help or ? to list commands.\n"
        PluginsShell.prompt = f'{plugin_type}> '

        # Make a local copy to avoid mutability/type variance issues while allowing Mapping covariance.
        self._plugins: dict[str, BasePlugin] = dict(plugins)
        self._plugin_type = plugin_type
        self._shell: BaseShell | None = None

    def getShell(self) -> BaseShell | None:
        return self._shell

    def do_list(self, arg):
        """List all available plugins."""
        displayPluginCategory(self._plugin_type, self._plugins)

    def do_load(self, name: str):
        """Load a specific plugin."""
        modName = ""
        className = ""
        try:
            idx = getInt(name)
            if idx is not None:
                if idx >= len(self._plugins):
                    print("Index not valid.")
                    return

                name = list(self._plugins.keys())[idx]

            plugin = self._plugins[name]

            # Create the shell class name dynamically
            className = self._plugin_type + "Shell"
            modName = "Cerberus.cmdShells." + className[0].lower() + className[1:]
            module = import_module(modName)
            pluginsClass = getattr(module, className)

            if pluginsClass:
                # Instantiate the shell, but do_open() will start the shell cmdLoop()
                self._shell = pluginsClass(plugin, self.manager)
            else:
                print(f"No shell found for plugin type: {self._plugin_type}")

        except KeyError:
            print(f"Unknown {self._plugin_type.lower()}: {name}")

        except Exception as e:
            print(f"Failed to create plugin shell: {modName}.{className} - {e}")

    def do_open(self, arg):
        """Opens a new shell or the currently loaded shell"""
        if self._shell is None:
            print("You need to load a shell first")

        if self._shell is not None:
            self._shell.cmdloop()
            self._shell = None
        else:
            print("You need to load a shell first")
