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
from Cerberus.database.mySqlDB import MySqlDB
from Cerberus.database.postgreSqlDB import PostgreSqlDB
from Cerberus.logConfig import getLogger, setupLogging
from Cerberus.manager import Manager

logger = getLogger("Shell")


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


def loadIni(inifile: str = "cerberus.ini") -> Tuple[str, str, DBInfo]:
    ini = iniconfig.IniConfig(inifile)
    if ini is None:
        logger.error(f"Failed to load {inifile} file!")
        exit(1)

    stationId = ini["Cerberus"]["identity"]
    dbName = ini["Cerberus"]["database"]
    dbInfo = DBInfo(
        host=ini[dbName]["host"],
        port=int(ini[dbName]["port"]),
        username=ini[dbName]["username"],
        password=ini[dbName]["password"],
        database=ini[dbName]["database"]
    )

    return stationId, dbName, dbInfo


SPLASH_DELAY = 0.05


def runShell(argv):
    parser = argparse.ArgumentParser(description="Cerberus Shell")
    parser.add_argument('-i', '--inifile', type=str, default='cerberus.ini', help='configuration filename (default: cerberus.ini)')
    args, unknown = parser.parse_known_args(argv)
    splash = show_image_splash(argv)

    setupLogging(logging.DEBUG)
    stationId, dbName, dbInfo = loadIni(args.inifile)
    logger.info(f"Cerberus:{stationId}")

    def splashUpdate(msg: str):
        if splash:
            splash.update_status(msg)
            dwell(SPLASH_DELAY)

    splashUpdate("Opening database...")

    try:
        if dbName == "FileDatabase":
            db = FileDatabase(dbInfo.database)
        elif dbName == "MySqlDatabase":
            db = MySqlDB(stationId, dbInfo)
        elif dbName == "PostgreSqlDatabase":
            db = PostgreSqlDB(stationId, dbInfo)
        else:
            raise ValueError(f"Unknown database type {dbName}")

        logger.info(f"Using {dbName}: {dbInfo.host}:{dbInfo.port}")

    except Exception as e:
        logger.error(f"Failed to connect to database: {dbInfo}")
        exit(1)

    try:
        manager = Manager(stationId, db, status_callback=splashUpdate)
    except Exception as e:
        logger.error(f"Failed to correctly load the plugins: {e}")
        exit(1)

    # Auto-hide splash after discovery completes
    if splash:
        QTimer.singleShot(1500, splash.close)

    with manager:
        try:
            MainShell(manager).cmdloop()

        except KeyboardInterrupt:
            pass

        except Exception as e:
            logger.exception(f"Unhandled exception in shell: {e}")

        finally:
            print("\nGoodbye")
