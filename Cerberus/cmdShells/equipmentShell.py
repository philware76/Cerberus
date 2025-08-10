import argparse

from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.manager import Manager
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment


class EquipShell(PluginsShell):
    def __init__(self, manager: Manager):
        pluginService = manager.pluginService
        super().__init__(manager, pluginService.equipPlugins, "Equipment")


class EquipmentShell(RunCommandShell):
    def __init__(self, equip: BaseEquipment, manager: Manager):
        EquipmentShell.intro = f"Welcome to Cerberus {equip.name} Equipment System. Type help or ? to list commands.\n"
        EquipmentShell.prompt = f"{equip.name}> "

        super().__init__(equip, manager)
        self.equip: BaseEquipment = equip
        self.config = {}

    def do_identity(self, arg):
        """Show the equipment identity (if initialised)"""
        ident = getattr(self.equip, "identity", None)
        if ident:
            print(str(ident))
        else:
            print("Identity not available (instrument not initialised?)")

    def do_setForStation(self, arg):
        """
        setForStation [--cal-date YYYY-MM-DD] [--cal-due YYYY-MM-DD]
        Upsert this initialised equipment and attach it to the current station.
        """

        if not self.equip.isInitialised():
            print("Equipment is not initialise. Can't set it to the database")
            return False

        parser = argparse.ArgumentParser(prog="setForStation", add_help=False)
        parser.add_argument("--cal-date", dest="cal_date")
        parser.add_argument("--cal-due", dest="cal_due")
        try:
            ns = parser.parse_args(arg.split())
        except SystemExit:
            print(parser.format_usage().strip())
            return False

        ip = str(self.equip.getParameterValue("Communication", "IP Address"))
        port = int(self.equip.getParameterValue("Communication", "Port") or 5025)
        timeout = int(self.equip.getParameterValue("Communication", "Timeout") or 1000)

        db = self.manager.db
        equip_id = db.upsertEquipment(
            self.equip.identity.manufacturer,
            self.equip.identity.model,
            self.equip.identity.serial,
            self.equip.identity.version,
            ip,
            port,
            timeout,
            calibration_date=ns.cal_date,
            calibration_due=ns.cal_due,
        )

        if equip_id is None:
            print("Failed to upsert equipment record.")
            return False

        if not hasattr(db, 'attachEquipmentToStation') or not db.attachEquipmentToStation(equip_id):  # type: ignore[attr-defined]
            print("Failed to attach equipment to station.")
            return False

        print(f"Equipment attached: id={equip_id}, serial={self.equip.identity.serial}, ip={ip}, port={port}")
        return False
        return False
