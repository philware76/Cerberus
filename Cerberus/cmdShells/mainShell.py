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
from Cerberus.database.fileDB import FileDB
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


def loadIni(inifile: str = "cerberus.ini", db_override: str | None = None) -> Tuple[str, str, DBInfo]:
    ini = iniconfig.IniConfig(inifile)
    if ini is None:
        logger.error(f"Failed to load {inifile} file!")
        exit(1)

    stationId = ini["Cerberus"]["identity"]

    # Use database override if provided, otherwise use the one from ini file
    if db_override:
        dbName = db_override
        logger.info(f"Using database override: {dbName}")
    else:
        dbName = ini["Cerberus"]["database"]

    # Validate that the database section exists in the ini file
    if dbName not in ini:
        logger.error(f"Database configuration '{dbName}' not found in {inifile}")
        exit(1)

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
    parser.add_argument('--db', type=str, help='override database name from ini file (e.g., FileDatabase, MySqlDatabase, PostgreSqlDatabase)')
    args, unknown = parser.parse_known_args(argv)
    splash = show_image_splash(argv)

    try:
        setupLogging(logging.DEBUG)
        stationId, dbName, dbInfo = loadIni(args.inifile, args.db)
        logger.info(f"Cerberus:{stationId}")
    except Exception as e:
        logger.error(f"Failed to read Ini file: {e}")
        exit(1)

    def splashUpdate(msg: str):
        if splash:
            splash.update_status(msg)
            dwell(SPLASH_DELAY)

    splashUpdate("Opening database...")

    try:
        if dbName == "FileDatabase":
            db = FileDB(stationId, dbInfo.database)
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
