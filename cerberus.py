# cerberus/testmanager.py
import argparse
import ast
import inspect
import argparse
import json
import shlex
from typing import Union
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton

import logging
import sys
import cmd

from gui.widgetGen import apply_parameters, create_all_parameters_ui
from logConfig import setupLogging
from plugins.baseParameters import BaseParameters
from plugins.equipment.baseEquipment import BaseEquipment
from plugins.tests.baseTest import BaseTest
from testManager import TestManager
from testRunner import TestRunner


def displayPlugins():
    displayPluginCategory("Equipment", manager.equipPlugins)
    displayPluginCategory("Product", manager.productPlugins)
    displayPluginCategory("Test", manager.testPlugins)


def displayPluginCategory(category_name, plugins):
    logging.info(f"Available {category_name} plugins:")
    for name, plugin in plugins.items():
        logging.info(f" - {name}: '{plugin.name}'")

    logging.info("")


class BaseShell(cmd.Cmd):
    def do_quit(self, arg):
        """Quits the shell immediately"""
        raise KeyboardInterrupt()


class EquipShell(BaseShell):
    intro = "Welcome to Cerberus Equipment System. Type help or ? to list commands.\n"
    prompt = 'Equipment> '

    def do_exit(self, arg):
        """Exit the Cerberus Equipment shell"""
        return True

    def do_list(self, arg):
        """List all of the Equipment"""
        displayPluginCategory("Equipment", manager.equipPlugins)

    def do_load(self, equipName):
        """Loads equipment"""
        try:
            equip = manager.equipPlugins[equipName]
            EquipmentShell(equip).cmdloop()
        except KeyError:
            print(f"Unknown equipment: {equipName}")


class CommsParser():
    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(prog="setIPComms", add_help=False)
        self.parser.add_argument("ip", help='IP Address of the device')
        self.parser.add_argument("port", type=int, help='Port number')


def get_base_methods(base_cls):
    return {
        name: method
        for name, method in inspect.getmembers(base_cls, predicate=inspect.isfunction)
        if not name.startswith('_')
    }


class EquipmentShell(BaseShell):
    def __init__(self, equip):
        EquipmentShell.intro = f"Welcome to Cerberus {equip.name} Equipment System. Type help or ? to list commands.\n"
        EquipmentShell.prompt = f"{equip.name}> "

        super().__init__()
        self.equip: BaseEquipment = equip
        self.config = {}

        self.base_cls = equip.__class__.__bases__[0]
        self.allowed_methods = get_base_methods(self.base_cls)
        self.parsers = self._buildParsers()

        self.comms = CommsParser()

    def _buildParsers(self):
        """Build ArgumentParsers for each allowed method based on its signature."""
        parsers = {}

        for name, method in self.allowed_methods.items():
            sig = inspect.signature(method)
            parser = argparse.ArgumentParser(prog=name, add_help=False)
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                # Check if parameter is Optional
                is_optional = self._is_optional_type(param.annotation)

                if is_optional:
                    # Optional parameters become optional arguments with --
                    parser.add_argument(f'--{param_name}', type=self._safe_eval_type, default=None)
                else:
                    # Required parameters remain positional
                    parser.add_argument(param_name, type=self._safe_eval_type)

            parsers[name] = parser

        return parsers

    def _is_optional_type(self, annotation):
        """Check if a type annotation represents an Optional type."""
        if annotation == inspect.Parameter.empty:
            return False

        # Check for typing.Optional or typing.Union[X, None]
        origin = getattr(annotation, '__origin__', None)
        if origin is Union:
            args = getattr(annotation, '__args__', ())
            # Optional[X] is equivalent to Union[X, None]
            return type(None) in args

        return False

    def _safe_eval_type(self, value):
        """Safely evaluate Python literals, fall back to string."""
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value

    def default(self, line):
        try:
            parts = shlex.split(line.strip())
        except ValueError as e:
            print(f"Error parsing command: {e}")
            return

        if not parts:
            raise ValueError("No arguments!")

        method_name = parts[0]
        args = parts[1:]

        if method_name not in self.allowed_methods:
            print(f"Error: '{method_name}' is not a valid command.")
            return

        parser = self.parsers[method_name]
        try:
            parsed_args = parser.parse_args(args)
            arg_values = vars(parsed_args)
            if 'self' in arg_values:
                del arg_values['self']

            method = getattr(self.equip, method_name)
            method(**arg_values)
        except SystemExit:
            # argparse throws this when parsing fails
            print(f"Usage error: {method_name} {parser.format_usage().strip()}")
        except Exception as e:
            print(f"Error calling method: {e}")

    def _format_type_annotation(self, annotation):
        """Format type annotation for clean display."""
        if annotation == inspect.Parameter.empty:
            return None

        # Convert to string and clean up common patterns
        type_str = str(annotation)

        # Remove 'typing.' prefix
        type_str = type_str.replace('typing.', '')

        # Handle <class 'type'> format
        if type_str.startswith("<class '") and type_str.endswith("'>"):
            type_str = type_str[8:-2]  # Remove <class '...'> wrapper

        return type_str

    def do_cmds(self, arg):
        """List the commands this equipment can execute"""
        if not arg:
            print("Available commands:-")
            for method_name, method in self.allowed_methods.items():
                sig = inspect.signature(method)

                # Build parameter list, excluding 'self'
                params = []
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue

                    # Add type annotation if available
                    formatted_type = self._format_type_annotation(param.annotation)
                    if formatted_type:
                        params.append(f"{param_name}: {formatted_type}")
                    else:
                        params.append(param_name)

                # Join parameters with spaces or commas as you prefer
                param_str = ' '.join(params)

                print(f"  {method_name} {param_str}")

        elif arg in self.parsers:
            self.parsers[arg].print_help()
        else:
            print(f"No help available for '{arg}'.")

    def do_exit(self, arg):
        """Exit the Cerberus Equipment shell"""
        return True

    def do_init(self, arg):
        """Initialises the Equipment"""
        if self.equip.initialise(self.config):
            print(f"Equipment Identity: {self.equip.identity}")

    def do_setIPComms(self, args):
        """Sets the IP Communication to the device"""
        try:
            args = self.comms.parser.parse_args(shlex.split(args))
            self.config["IPAddress"] = args.ip
            self.config["Port"] = args.port

        except SystemExit:
            logging.warning("Failed to parse your Set IP Comms command")

    def do_finalise(self, arg):
        if self.equip.initialised:
            self.equip.finalise()


class ProductShell(BaseShell):
    intro = "Welcome to Cerberus Product System. Type help or ? to list commands.\n"
    prompt = 'Product> '

    def do_exit(self, arg):
        """Exit the Cerberus Product shell"""
        return True

    def do_list(self, arg):
        """List all of the Products"""
        displayPluginCategory("Product", manager.productPlugins)


class TestsShell(BaseShell):
    intro = "Welcome to Cerberus Test System. Type help or ? to list commands.\n"
    prompt = 'Tests> '

    def do_exit(self, arg):
        """Exit the Cerberus Test shell"""
        return True

    def do_list(self, arg):
        """List all of the Tests"""
        displayPluginCategory("Test", manager.testPlugins)

    def do_load(self, testName):
        """Loads a test"""
        try:
            test = manager.testPlugins[testName]
            TestShell(test).cmdloop()
        except KeyError:
            print(f"Unknown test: {testName}")


class TestShell(BaseShell):
    def __init__(self, test):
        TestShell.intro = f"Welcome to Cerberus {test.name} Test System. Type help or ? to list commands.\n"
        TestShell.prompt = f"{test.name}> "

        super().__init__()
        self.test: BaseTest = test

    def do_exit(self, arg):
        """Exit the Cerberus Test shell"""
        return True

    def do_run(self, arg):
        """Run the loaded test"""
        testRunner.runTest(self.test)

    def do_params(self, arg):
        """Show the test parameters"""
        print(self.test.parameters)

    def do_getParams(self, group):
        """Show the test parameters as json string"""
        if group in self.test.parameters.keys():
            dict = self.test.parameters[group].to_dict()
            print(json.dumps(dict))
        else:
            print(f"Parameter group '{group}' does not exist")

    def do_setParams(self, line):
        """
        Set the parameters from a JSON string.
        Usage:
            setParams "Voltage Parameters" '{"param1": {"name": ..., ...}}'
        """
        try:
            # Use shlex to properly parse quoted strings
            parts = shlex.split(line)
            if len(parts) != 2:
                print("Usage: setParams \"Group Name\" '{...json...}'")
                return

            group, json_str = parts
            params = BaseParameters.from_dict(json.loads(json_str))
            self.test.parameters[group] = params
            print(f"Parameters for '{group}' set successfully.")

        except json.JSONDecodeError as e:
            print("JSON decoding failed:", e)
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

        groups = self.test.parameters

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

        window.setWindowTitle("f{self.test.name} Parameters")
        window.resize(400, 300)
        window.show()

        paramApp.exec()


class Shell(BaseShell):
    intro = "Welcome to Cerberus Test System. Type help or ? to list commands.\n"
    prompt = 'Cerberus> '

    def do_exit(self, arg):
        """Exit Cerberus shell and exit the application"""
        print("Goodbye")
        exit(0)

    def do_equip(self, arg):
        """Go into the Equipment shell subsystem"""
        EquipShell().cmdloop()

    def do_products(self, arg):
        """Go into the Product shell subsystem"""
        ProductShell().cmdloop()

    def do_tests(self, arg):
        """Go into the Test shell subsystem"""
        TestsShell().cmdloop()


if __name__ == "__main__":
    setupLogging(logging.DEBUG)

    app = QApplication(sys.argv)
    manager = TestManager()
    testRunner = TestRunner(manager)

    try:
        Shell().cmdloop()
    except KeyboardInterrupt:
        print("\nGoodbye\n")
