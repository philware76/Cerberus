# cerberus/testmanager.py
import argparse
import inspect
import argparse
import json
import shlex
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


class EquipShell(cmd.Cmd):
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


class EquipmentShell(cmd.Cmd):
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
                annotation = param.annotation if param.annotation is not inspect.Parameter.empty else str
                parser.add_argument(param_name, type=annotation)

            parsers[name] = parser

        return parsers

    def default(self, line):
        parts = line.strip().split()
        if not parts:
            return

        method_name = parts[0]
        args = parts[1:]

        if method_name not in self.allowed_methods:
            print(f"Error: '{method_name}' is not a valid command.")
            return

        parser = self.parsers[method_name]
        try:
            parsed_args = parser.parse_args(args)
            arg_values = vars(parsed_args)
            method = getattr(self.equip, method_name)
            method(**arg_values)
        except SystemExit:
            # argparse throws this when parsing fails
            print(f"Usage error: {method_name} {parser.format_usage().strip()}")
        except Exception as e:
            print(f"Error calling method: {e}")

    def do_help(self, arg):
        if not arg:
            print("Available commands (from BaseSpectrumAnalyser):")
            for method_name, method in self.allowed_methods.items():
                sig = inspect.signature(method)
                print(f"  {method_name}{sig}")
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
            pass

    def do_finalise(self, arg):
        if self.equip.initialised:
            self.equip.finalise()


class ProductShell(cmd.Cmd):
    intro = "Welcome to Cerberus Product System. Type help or ? to list commands.\n"
    prompt = 'Product> '

    def do_exit(self, arg):
        """Exit the Cerberus Product shell"""
        return True

    def do_list(self, arg):
        """List all of the Products"""
        displayPluginCategory("Product", manager.productPlugins)


class TestsShell(cmd.Cmd):
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


class TestShell(cmd.Cmd):
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


class Shell(cmd.Cmd):
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
