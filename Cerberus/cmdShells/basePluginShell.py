import json

from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.gui.helpers import displayParametersUI
from Cerberus.manager import Manager
from Cerberus.plugins.baseParameters import BaseParameters
from Cerberus.plugins.basePlugin import BasePlugin


class BasePluginShell(BaseShell):
    def __init__(self, plugin: BasePlugin, manager: Manager):
        super().__init__(manager)
        self.plugin = plugin

    def do_txtParams(self, arg):
        """Show the test parameters in a human readable way"""
        for groupParams in self.plugin._groupParams.values():
            print(groupParams.groupName)
            for key, value in list(groupParams.items()):
                print(f"  - {key}: {value}")

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
            payload = json.loads(line)
        except json.JSONDecodeError as e:
            print("JSON decoding failed:", e)
            return

        try:
            group_name = payload["groupName"]
            raw_params = payload["parameters"]
        except KeyError as e:
            print(f"Missing expected key: {e}. Expecting 'groupName' and 'parameters'.")
            return

        # Validate group existence
        if group_name not in self.plugin._groupParams:
            print(f"Error: Group '{group_name}' does not exist in test parameters.")
            return

        existing_group: BaseParameters = self.plugin._groupParams[group_name]

        # Validate that all provided parameter names already exist (prevent silent drops / typos)
        unknown = [p for p in raw_params.keys() if p not in existing_group]
        if unknown:
            print(f"Error: Unknown parameter name(s) for group '{group_name}': {unknown}")
            return

        try:
            # Build a new parameter group instance (atomic replacement on success)
            new_group = BaseParameters.from_dict(group_name, raw_params)
        except Exception as e:  # Construction failed; leave old group intact
            print("Failed to construct new parameter group:", e)
            return

        # All validation passed, commit replacement
        self.plugin._groupParams[group_name] = new_group
        print(f"\nUpdated {group_name} parameters:")
        for value in list(new_group.values()):
            print(" - " + str(value))
        print()

    def do_uiParams(self, arg):
        """Show a GUI for the parameters to edit"""
        try:
            displayParametersUI(self.plugin.name, self.plugin._groupParams)
        except ImportError as e:
            print("GUI not available (PySide6 not installed?)")

    def do_init(self, arg):
        """Initialises the plugin"""
        if self.plugin.initialise():
            print("Initialised\n")
        else:
            print("Not initialised\n")

    def do_finalise(self, arg):
        """Finalises and closes the equipment"""
        if self.plugin.finalise():
            print("Finalised\n")
        else:
            print("Not finalises\n")

    def do_exit(self, arg) -> bool:
        """Finalise (close) and exit the equipment shell"""
        self.do_finalise(arg)
        return super().do_exit(arg)
