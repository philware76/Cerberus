import json

from Cerberus.cerberusManager import CerberusManager
from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.gui.helpers import displayParametersUI
from Cerberus.plugins.baseParameters import BaseParameters
from Cerberus.plugins.basePlugin import BasePlugin


class BasePluginShell(BaseShell):
    def __init__(self, plugin: BasePlugin, manager: CerberusManager):
        self.plugin = plugin
        self.manager = manager

        super().__init__()

    def do_txtParams(self, arg):
        """Show the test parameters in a human readable way"""
        for groupParams in self.plugin._groupParams.values():
            print(groupParams.groupName)
            for value in list(groupParams.values()):
                print(" - " + str(value))

        print()

    def do_listGroups(self, line):
        """List the parameter groups"""
        for name in self.plugin._groupParams.keys():
            print(name)

        print()

    def do_getGroupParams(self, group):
        """Show the test parameters for the specified group as json.dumps(params.to_dict()) string"""
        if group in self.plugin._groupParams.keys():
            params = self.plugin._groupParams[group].to_dict()["parameters"]
            print(json.dumps(params))
        else:
            print(f"Parameter group '{group}' does not exist")

        print()

    def do_setGroupParams(self, line):
        """
        Set a group parameters from a JSON string.
        Usage:
            setParams "{'GroupName':<groupName> }, {"Parameters":{"param1": {"name": ..., ...}}'
        """
        try:
            # Parse the JSON string into a dictionary
            jsonTxt = json.loads(line)
            groupName = jsonTxt["groupName"]
            params = jsonTxt["parameters"]
            # Ensure that the group exists in the test parameters
            if groupName in self.plugin._groupParams:
                # Convert the dictionary into a BaseParameters (or subclass) object
                params = BaseParameters.from_dict(groupName, params)
                self.plugin._groupParams[groupName] = params
                print(f"\nNew {groupName} parameters:")
                for value in list(params.values()):
                    print(" - " + str(value))

                print()
            else:
                print(f"Error: Group '{groupName}' does not exist in test parameters.")

        except json.JSONDecodeError as e:
            print("JSON decoding failed:", e)
        except KeyError as e:
            print(f"Missing expected key in parameters: {e}")
        except Exception as e:
            print("Error setting parameters:", e)
        
    def do_uiParams(self, arg):
        """Show a GUI for the parameters to edit"""
        try:
            import importlib
            gui_module = importlib.import_module("Cerberus.gui.display_ui")
            gui_module.displayParametersUI(self.plugin._groupParams)
        except ImportError as e:
            print("GUI not available (PySide6 not installed?)")

    def do_init(self, arg):
        """Initialises the plugin"""
        if self.plugin.initialise(self.config):
            print(f"Identity: {self.plugin.identity}")

    def do_finalise(self, arg):
        """Finalises and closes the equipment"""
        if self.plugin.initialised:
            self.plugin.finalise()
