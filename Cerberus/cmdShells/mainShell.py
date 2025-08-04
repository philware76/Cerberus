import argparse
import logging
from typing import Tuple

import iniconfig
from PySide6.QtWidgets import QApplication

from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.cmdShells.databaseShell import DatabaseShell
from Cerberus.cmdShells.equipmentShell import EquipShell
from Cerberus.cmdShells.ManagerShell import ManagerShell
from Cerberus.cmdShells.planShell import PlanShell
from Cerberus.cmdShells.productShell import ProductsShell
from Cerberus.cmdShells.testShell import TestsShell
from Cerberus.common import DBInfo
from Cerberus.database import Database
from Cerberus.logConfig import setupLogging
from Cerberus.manager import Manager


class MainShell(BaseShell):
    intro = "Welcome to Cerberus Shell. Type help or ? to list commands.\n"
    prompt = 'Cerberus> '

    def __init__(self, manager:Manager):
        super().__init__(manager)

    def do_equip(self, arg):
        """Go into the Equipment shell subsystem"""
        EquipShell(self.manager).cmdloop()

    def do_products(self, arg):
        """Go into the Product shell subsystem"""
        ProductsShell(self.manager).cmdloop()

    def do_tests(self, arg):
        """Go into the Test shell subsystem"""
        TestsShell(self.manager).cmdloop()

    def do_database(self, arg):
        """Go into the Database shell subsystem"""
        DatabaseShell(self.manager).cmdloop()

    def do_manager(self, arg):
        """Go into the Manager shell subsystem"""
        ManagerShell(self.manager).cmdloop()

    def do_plan(self, arg):
        """Go into the Plan shell subsystem"""
        PlanShell(self.manager).cmdloop()

    def do_quit(self, arg):
        """Quits the shell immediately"""
        print("Exiting Cerberus shell...")
        self.manager.finalize()
        super().do_quit(arg)

def loadIni(inifile: str = "cerberus.ini") -> Tuple[str, DBInfo]:
    ini = iniconfig.IniConfig(inifile)
    if ini is None:
        logging.error(f"Failed to load {inifile} file!")
        exit(1)

    stationId = ini["cerberus"]["identity"]
    dbInfo = DBInfo(
        host=ini["database"]["host"],
        username=ini["database"]["username"],
        password=ini["database"]["password"],
        database=ini["database"]["database"]
    )

    return stationId, dbInfo


def runShell(argv):
    setupLogging(logging.DEBUG)

    parser = argparse.ArgumentParser(description="Cerberus Shell")
    parser.add_argument('-f', '--filedb', type=str, help='Use FileDatabase with the given filename')
    parser.add_argument('-i', '--inifile', type=str, default='cerberus.ini', help='INI filename (default: cerberus.ini)')
    args, unknown = parser.parse_known_args(argv)

    app = QApplication(argv)
    stationId, dbInfo = loadIni(args.inifile)
    logging.info(f"Cerberus:{stationId}")

    if args.filedb:
        from Cerberus.fileDatabase import FileDatabase
        db = FileDatabase(args.filedb)
        logging.info(f"Using FileDatabase: {args.filedb}")
    else:
        db = Database(stationId, dbInfo)
        logging.info("Using MySQL Database")

    manager = Manager(db)

    try:
        MainShell(manager).cmdloop()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Shell failed to start with: {e}")

    finally:
        print("\nGoodbye")
        exit(0)
