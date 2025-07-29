import logging
import sys

from logConfig import setupLogging
from PySide6.QtWidgets import QApplication

from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.cmdShells.equipmentShell import EquipShell
from Cerberus.cmdShells.productShell import ProductsShell
from Cerberus.cmdShells.testShell import TestsShell
from Cerberus.testManager import TestManager
from Cerberus.testRunner import TestRunner


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
