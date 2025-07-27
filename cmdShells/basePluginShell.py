import json
import shlex
from cmdShells.baseShell import BaseShell
from gui.widgetGen import apply_parameters, create_all_parameters_ui
from plugins.baseParameters import BaseParameters
from plugins.basePlugin import BasePlugin

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton

from testManager import TestManager


class BasePluginShell(BaseShell):
    def __init__(self, plugin: BasePlugin, manager: TestManager):
        self.plugin = plugin
        self.manager = manager

        super().__init__()

    def do_params(self, arg):
        """Show the test parameters in a human readable way"""
        for groupParams in self.plugin.parameters.values():
            print(groupParams.groupName)
            for value in list(groupParams.values()):
                print(" - " + str(value))
        
        print()

    def do_getParamGroup(self, group):
        """Show the test parameters for the specified group as json.dumps(params.to_dict()) string"""
        if group in self.plugin.parameters.keys():
            pluginDict = self.plugin.parameters[group].to_dict()
            print(json.dumps(pluginDict))
        else:
            print(f"Parameter group '{group}' does not exist")

    def do_setParams(self, line):
        """
        Set a group parameters from a JSON string.
        Usage:
            setParams "RF Params" '{"param1": {"name": ..., ...}}'
        """
        try:
            # Use shlex to properly parse quoted strings
            parts = shlex.split(line)
            if len(parts) != 2:
                print("Usage: setParams \"Group Name\" '{...json...}'")
                return

            group, json_str = parts
            # Parse the JSON string into a dictionary
            params_dict = json.loads(json_str)

            # Ensure that the group exists in the test parameters
            if group in self.plugin.parameters:
                # Convert the dictionary into a BaseParameters (or subclass) object
                params = BaseParameters.from_dict(params_dict)
                self.plugin.parameters[group] = params
                print(f"Parameters for '{group}' set successfully.")
            else:
                print(f"Error: Group '{group}' does not exist in test parameters.")

        except json.JSONDecodeError as e:
            print("JSON decoding failed:", e)
        except KeyError as e:
            print(f"Missing expected key in parameters: {e}")
        except Exception as e:
            print("Error setting parameters:", e)

    def do_showParams(self, arg):
        """Show a GUI for the parameters to edit"""
        # Make sure QApplication exists; create one if it doesn't
        paramApp = QApplication.instance()
        if paramApp is None:
            paramApp = QApplication([])

        window = QWidget()
        layout = QVBoxLayout(window)

        groups = self.plugin.parameters

        ui, widget_map = create_all_parameters_ui(groups)
        layout.addWidget(ui)

        apply_btn = QPushButton("Apply")
        layout.addWidget(apply_btn)

        def on_apply():
            apply_parameters(groups, widget_map)
            print("Updated parameters:")
            for group in groups.values():
                for param in group.values():
                    print(f"{group.groupName} -> {param.name}: {param.value} {param.units}")

        apply_btn.clicked.connect(on_apply)

        window.setWindowTitle(f"{self.plugin.name} Parameters")
        window.resize(400, 300)
        window.show()

        paramApp.exec()

    def do_init(self, arg):
        """Initialises the plugin"""
        if self.plugin.initialise(self.config):
            print(f"Identity: {self.plugin.identity}")

    def do_finalise(self, arg):
        """Finalises and closes the equipment"""
        if self.plugin.initialised:
            self.plugin.finalise()
