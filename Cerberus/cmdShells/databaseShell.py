import logging

from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.manager import Manager


class DatabaseShell(BaseShell):
    intro = "Cerberus Database Shell. Type help or ? to list commands."
    prompt = "Database> "

    def __init__(self, manager: Manager):
        super().__init__(manager)

    def do_wipeDB(self, arg):
        """Drop equipment, station and testplans tables (DANGEROUS)."""
        confirm = input("Type 'YES' to confirm wiping the database: ")
        if confirm != 'YES':
            print("Aborted.")
            return

        self.manager.db.wipeDB()

    def do_get_chamber(self, arg):
        "Get the chamber class name for this station from the database"
        chamber = self.manager.chamberService.loadChamber()
        print(f"Chamber class: {chamber}")

    def do_set_chamber(self, arg):
        "Set the chamber class name for this station in the database. Usage: set_chamber <ClassName>"
        if not arg:
            print("Please provide a chamber class name.")
            return

        if self.manager.chamberService.saveChamber(arg):
            print(f"Chamber class set to: {arg}")
        else:
            print(f"Could not set Chamber type to {arg}")

    def do_getStationEquipment(self, arg):
        """List equipment attached to this station."""
        try:
            rows = self.manager.db.listStationEquipment()
            if not rows:
                print("No equipment attached.")
                return
            for e in rows:
                print(f"id={e.get('id')} serial={e.get('serial')} "
                      f"{e.get('manufacturer')} {e.get('model')} "
                      f"IP={e.get('ip_address')}:{e.get('port')} "
                      f"timeout={e.get('timeout_ms')}ms "
                      f"cal_date={e.get('calibration_date') or 'N/A'} "
                      f"cal_due={e.get('calibration_due') or 'N/A'}")

        except Exception as ex:
            print(f"Error listing station equipment: {ex}")

        return False

    def do_attachEquipment(self, arg):
        """attachEquipment <equipmentId> : Attach an existing equipment row to this station."""
        if not arg.strip():
            print("Usage: attachEquipment <equipmentId>")
            return False
        try:
            equip_id = int(arg.strip())
        except ValueError:
            print("equipmentId must be an integer")
            return False

        if not hasattr(self.manager.db, 'attachEquipmentToStation'):
            print("Backend does not support station-centric attachment yet.")
            return False
        if self.manager.db.attachEquipmentToStation(equip_id):  # type: ignore[attr-defined]
            print(f"Equipment {equip_id} attached to station.")
        else:
            print(f"Failed to attach equipment {equip_id} to station.")
        return False
