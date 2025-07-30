from importlib import import_module
from typing import Dict, Type

from Cerberus.cerberusManager import CerberusManager
from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.cmdShells.common import displayPluginCategory, getInt
from Cerberus.plugins.basePlugin import BasePlugin


class PluginsShell(BaseShell):
    """A base shell class for interacting with plugin dictionaries."""

    def __init__(self, manager:CerberusManager, plugins: Dict[str, Type[BasePlugin]], plugin_type: str):
        super().__init__()
        PluginsShell.intro = f"Welcome to Cerberus {plugin_type} System. Type help or ? to list commands.\n"
        PluginsShell.prompt = f'{plugin_type}> '
      
        self.manager = manager
        self.plugins = plugins
        self.plugin_type = plugin_type

    def do_list(self, arg):
        """List all available plugins."""
        displayPluginCategory(self.plugin_type, self.plugins)

    def do_load(self, name):
        """Load a specific plugin."""
        try:
            idx = getInt(name)
            if idx is not None:
                name = list(self.plugins.keys())[idx]

            plugin = self.plugins[name]

            # Create the shell class name dynamically
            className = self.plugin_type + "Shell"
            modName = "Cerberus.cmdShells." + className[0].lower() + className[1:]
            module = import_module(modName)
            pluginsClass = getattr(module, className) 

            if pluginsClass:
                # Instantiate the shell and start the command loop
                shell = pluginsClass(plugin, self.manager)
                shell.cmdloop()
            else:
                print(f"No shell found for plugin type: {self.plugin_type}")
            
        except KeyError:
            print(f"Unknown {self.plugin_type.lower()}: {name}")

        except Exception as e:
            print(f"Failed to create plugin shell: {modName}.{className} - {e}")
