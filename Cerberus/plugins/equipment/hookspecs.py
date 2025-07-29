### Hooks Specification File for the Equipment Plugins
###
### This file defines the hookspecs for the equipment plugins.
### It is used by the PluginDiscovery class to dynamically load and register "Equipment" plugins.
###
### The hookspecs define the methods that plugins must implement to be recognized as valid equipment plugins.
###
### This file should be placed in the `plugins/equipment` directory and named `hookspecs.py`.
### The name of the Equipment plugins need to end with `Equipment.py` to be recognized by the PluginDiscovery for Equipment class.
###

from Cerberus.plugins.basePlugin import hookspec


class EquipmentSpec:
    @hookspec
    def createEquipmentPlugin():
        """create an equipment plugin"""
        pass
