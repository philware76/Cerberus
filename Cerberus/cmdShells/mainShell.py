import logging

from PySide6.QtWidgets import QApplication

from Cerberus.cerberusManager import CerberusManager
from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.cmdShells.equipmentShell import EquipShell
from Cerberus.cmdShells.productShell import ProductsShell
from Cerberus.cmdShells.testShell import TestsShell
from Cerberus.logConfig import setupLogging


class MainShell(BaseShell):
    intro = "Welcome to Cerberus Shell. Type help or ? to list commands.\n"
    prompt = 'Cerberus> '

    def __init__(self, manager:CerberusManager):
        self.manager = manager
        super().__init__()

    def do_equip(self, arg):
        """Go into the Equipment shell subsystem"""
        EquipShell(self.manager).cmdloop()

    def do_products(self, arg):
        """Go into the Product shell subsystem"""
        ProductsShell(self.manager).cmdloop()

    def do_tests(self, arg):
        """Go into the Test shell subsystem"""
        TestsShell(self.manager).cmdloop()


def runShell(argv):
    setupLogging(logging.DEBUG)

    app = QApplication(argv)
    manager = CerberusManager()
    
    try:
        MainShell(manager).cmdloop()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Shell failed to start with: {e}")

    finally:
        print("\nGoodbye")
        exit(0)
