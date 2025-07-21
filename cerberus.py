# cerberus/testmanager.py
import argparse
import shlex
from PySide6.QtWidgets import QApplication

import logging
import sys
import cmd

from logConfig import setupLogging
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


class EquipmentShell(cmd.Cmd):
    def __init__(self, equip):
        EquipmentShell.intro = f"Welcome to Cerberus {equip.name} Equipment System. Type help or ? to list commands.\n"
        EquipmentShell.prompt = f"{equip.name}> "

        super().__init__()
        self.equip: BaseEquipment = equip
        self.config = {}

        self.comms = CommsParser()

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
        print(self.test.Parameters)


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

    Shell().cmdloop()
