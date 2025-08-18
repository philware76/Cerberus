import argparse
import logging
from typing import Tuple

import iniconfig
from PySide6.QtCore import QTimer

from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.cmdShells.databaseShell import DatabaseShell
from Cerberus.cmdShells.equipmentShell import EquipShell
from Cerberus.cmdShells.helpers import show_image_splash
from Cerberus.cmdShells.ManagerShell import ManagerShell
from Cerberus.cmdShells.planShell import PlanShell
from Cerberus.cmdShells.productShell import ProductsShell
from Cerberus.cmdShells.testShell import TestsShell
from Cerberus.common import DBInfo, dwell
from Cerberus.database.fileDatabase import FileDatabase
from Cerberus.database.genericDB import GenericDB
from Cerberus.logConfig import setupLogging
from Cerberus.manager import Manager


class MainShell(BaseShell):
    intro = "Welcome to Cerberus Shell. Type help or ? to list commands.\n"
    prompt = 'Cerberus> '

    def __init__(self, manager: Manager):
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
    parser = argparse.ArgumentParser(description="Cerberus Shell")
    parser.add_argument('-f', '--filedb', type=str, help='Use FileDatabase with the given filename')
    parser.add_argument('-i', '--inifile', type=str, default='cerberus.ini', help='configuration filename (default: cerberus.ini)')
    args, unknown = parser.parse_known_args(argv)
    splash = show_image_splash(argv)

    setupLogging(logging.DEBUG)
    stationId, dbInfo = loadIni(args.inifile)
    logging.info(f"Cerberus:{stationId}")

    if args.filedb:
        db = FileDatabase(args.filedb)
        logging.info(f"Using FileDatabase: {args.filedb}")
    else:
        # db = Database(stationId, dbInfo)
        db = GenericDB(stationId, dbInfo)
        logging.info(f"Using MySQL: {dbInfo.host}:{dbInfo.port}")

    # Provide status callback if splash exists
    def _status(msg: str):
        if splash:
            splash.update_status(msg)
            dwell(0.05)

        # Instantiate manager (plugin discovery runs in constructor)
    manager = Manager(stationId, db, status_callback=_status)

    # Auto-hide splash after discovery completes
    if splash:
        QTimer.singleShot(1500, splash.close)

    with manager:

        try:
            MainShell(manager).cmdloop()

        except KeyboardInterrupt:
            pass

        except Exception as e:
            logging.exception("Unhandled exception in shell")

        finally:
            print("\nGoodbye")
