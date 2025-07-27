from typing import Dict, Type

from cmdShells.baseShell import BaseShell
from cmdShells.common import displayPluginCategory, getInt
from plugins.basePlugin import BasePlugin


class PluginsShell(BaseShell):
    """A base shell class for interacting with plugin dictionaries."""

    def __init__(self, plugins: Dict[str, Type[BasePlugin]], plugin_type: str):
        super().__init__()
        PluginsShell.intro = f"Welcome to Cerberus {plugin_type} System. Type help or ? to list commands.\n"
        PluginsShell.prompt = f'{plugin_type}> '
      
        self.plugins = plugins
        self.plugin_type = plugin_type

    def do_list(self, arg):
        """List all available plugins."""
        displayPluginCategory(self.plugin_type, self.plugins)

    def do_load(self, name):
        """Load a specific plugin."""
        try:
            if idx := getInt(name):
                name = list(self.plugins.keys())[idx]

            plugin = self.plugins[name]

            # Create the shell class name dynamically
            shell_class_name = self.plugin_type + "Shell"

            # Get the shell class using globals()
            shell_class = globals().get(shell_class_name)

            if shell_class:
                # Instantiate the shell and start the command loop
                plugin_shell = shell_class(self)
                plugin_shell.cmdloop()
            else:
                print(f"No shell found for plugin type: {self.plugin_type}")
            
        except KeyError:
            print(f"Unknown {self.plugin_type.lower()}: {name}")
