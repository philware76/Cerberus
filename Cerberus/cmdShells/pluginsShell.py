from importlib import import_module
from typing import Dict, Type

from Cerberus.cerberusManager import Manager
from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.cmdShells.common import displayPluginCategory, getInt
from Cerberus.plugins.basePlugin import BasePlugin


class PluginsShell(BaseShell):
    """A base shell class for interacting with plugin dictionaries."""

    def __init__(self, manager:Manager, plugins: Dict[str, Type[BasePlugin]], plugin_type: str):
        super().__init__()
        PluginsShell.intro = f"Welcome to Cerberus {plugin_type} System. Type help or ? to list commands.\n"
        PluginsShell.prompt = f'{plugin_type}> '
      
        self._manager = manager
        self._plugins = plugins
        self._plugin_type = plugin_type
        self._shell: BaseShell | None = None

    def getShell(self) -> BaseShell | None:
        return self._shell

    def do_list(self, arg):
        """List all available plugins."""
        displayPluginCategory(self._plugin_type, self._plugins)

    def do_load(self, name):
        """Load a specific plugin."""
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
                # Instantiate the shell and start the command loop
                self._shell = pluginsClass(plugin, self._manager)
            else:
                print(f"No shell found for plugin type: {self._plugin_type}")
            
        except KeyError:
            print(f"Unknown {self._plugin_type.lower()}: {name}")

        except Exception as e:
            print(f"Failed to create plugin shell: {modName}.{className} - {e}")

    def do_open(self, arg):
        """Opens a new shell or the currently loaded shell"""
        if self._shell is None and arg != '':
            self.do_load(arg)
            if self._shell is None:
                return
        
        if self._shell is not None:
            self._shell.cmdloop()
            self._shell = None
        else:
            print("You need to load a shell first")