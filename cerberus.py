import logging
import sys

from cmdShells.baseShell import BaseShell
from cmdShells.equipmentShell import EquipShell
from cmdShells.productShell import ProductsShell
from cmdShells.testShell import TestsShell

from logConfig import setupLogging

from testManager import TestManager
from testRunner import TestRunner

from PySide6.QtWidgets import QApplication

import readline


class Shell(BaseShell):
    intro = "Welcome to Cerberus Test System. Type help or ? to list commands.\n"
    prompt = 'Cerberus> '

    def do_equip(self, arg):
        """Go into the Equipment shell subsystem"""
        EquipShell(manager).cmdloop()

    def do_products(self, arg):
        """Go into the Product shell subsystem"""
        ProductsShell(manager).cmdloop()

    def do_tests(self, arg):
        """Go into the Test shell subsystem"""
        TestsShell(manager).cmdloop()


if __name__ == "__main__":
    setupLogging(logging.DEBUG)

    app = QApplication(sys.argv)
    manager = TestManager()
    testRunner = TestRunner(manager)

    try:
        Shell().cmdloop()
    except KeyboardInterrupt:
        pass

    finally:
        print("\nGoodbye")
        exit(0)
