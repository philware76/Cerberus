import argparse
import logging
from typing import Tuple

import iniconfig
from PySide6.QtWidgets import QApplication
from tabulate import tabulate

from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.cmdShells.common import is_valid_ip
from Cerberus.cmdShells.databaseShell import DatabaseShell
from Cerberus.cmdShells.equipmentShell import EquipShell
from Cerberus.cmdShells.ManagerShell import ManagerShell
from Cerberus.cmdShells.planShell import PlanShell
from Cerberus.cmdShells.productShell import ProductsShell
from Cerberus.cmdShells.testShell import TestsShell
from Cerberus.common import DBInfo
from Cerberus.database.database import Database
from Cerberus.database.fileDatabase import FileDatabase
from Cerberus.ethDiscovery import EthDiscovery
from Cerberus.logConfig import setupLogging
from Cerberus.manager import Manager


class MainShell(BaseShell):
    intro = "Welcome to Cerberus Shell. Type help or ? to list commands.\n"
    prompt = 'Cerberus> '

    def __init__(self, manager: Manager):
        super().__init__(manager)
        self.devices = {}
        self.device = None

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

    def do_discover(self, arg):
        """Discovery NESIE devices on the network.
        You can specify the Key to sort on too."""
        if arg is not None and arg != "":
            sortField = arg
        else:
            sortField = "ID"

        self.devices = EthDiscovery().search()
        if self.devices is not None and len(self.devices) > 0:
            self.devices = sorted(self.devices, key=lambda x: x[sortField])
            print(tabulate(self.devices, headers="keys", tablefmt="pretty"))
        else:
            print("No devices found!")

    def do_select(self, arg):
        """Select a device to use"""
        if arg is None or arg == "":
            print("You need to specify the IP Address of the device to select")
            return

        if not is_valid_ip(arg):
            print("You must use a valid IP Address format")
            return

        matches = [d for d in self.devices if d["IP Address"] == arg]
        if len(matches) == 0:
            print(f"Device at IP Address '{arg}' is not available. Run discover again.")
            return

        self.device = matches[0]
        print(f"Selected device: {self.device}")


def loadIni(inifile: str = "cerberus.ini") -> Tuple[str, DBInfo]:
    ini = iniconfig.IniConfig(inifile)
    if ini is None:
        logging.error(f"Failed to load {inifile} file!")
        exit(1)

    stationId = ini["cerberus"]["identity"]
    dbInfo = DBInfo(
        host=ini["database"]["host"],
        port=int(ini["database"]["port"]),
        username=ini["database"]["username"],
        password=ini["database"]["password"],
        database=ini["database"]["database"]
    )

    return stationId, dbInfo


def runShell(argv):
    setupLogging(logging.DEBUG)

    parser = argparse.ArgumentParser(description="Cerberus Shell")
    parser.add_argument('-f', '--filedb', type=str, help='Use FileDatabase with the given filename')
    parser.add_argument('-i', '--inifile', type=str, default='cerberus.ini', help='configuration filename (default: cerberus.ini)')
    args, unknown = parser.parse_known_args(argv)

    app = QApplication(argv)
    stationId, dbInfo = loadIni(args.inifile)
    logging.info(f"Cerberus:{stationId}")

    if args.filedb:
        db = FileDatabase(args.filedb)
        logging.info(f"Using FileDatabase: {args.filedb}")
    else:
        db = Database(stationId, dbInfo)
        logging.info(f"Using MySQL: {dbInfo.host}:{dbInfo.port}")

    manager = Manager(stationId, db)

    try:
        MainShell(manager).cmdloop()
    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(f"Shell Exception: {e}")

    finally:
        print("\nGoodbye")
        exit(0)
