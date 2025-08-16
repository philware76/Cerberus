import argparse
from typing import Any, cast  # added for identity check typing

from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.manager import Manager
from Cerberus.plugins.equipment.baseEquipment import BaseCommsEquipment
from Cerberus.plugins.equipment.commsInterface import CommsInterface


class EquipShell(PluginsShell):
    def __init__(self, manager: Manager):
        pluginService = manager.pluginService
        super().__init__(manager, pluginService.equipPlugins, "Equipment")


class EquipmentShell(RunCommandShell):
    def __init__(self, equip: BaseCommsEquipment, manager: Manager):
        EquipmentShell.intro = f"Welcome to Cerberus {equip.name} Equipment shell. Type help or ? to list commands.\n"
        EquipmentShell.prompt = f"{equip.name}> "

        super().__init__(equip, manager)
        self.equip: BaseCommsEquipment = equip
        self.config = {}

    def do_identity(self, arg):
        """Show the equipment identity (if initialised)"""
        if self.equip.isInitialised():
            print(self.equip.identity)
        else:
            print("Equipment/Device is not initialised.")

    def do_checkId(self, arg):
        """checkId : Compare initialised equipment identity with DB (lookup by model & station)."""
        if not self.equip.isInitialised():
            print("Equipment is not initialised; run init first.")
            return False

        ident = self.equip.identity
        if not ident or not ident.serial:
            print("Equipment identity/serial unavailable.")
            return False

        # Use the model from the identity (not the plugin name) for DB lookup
        rec = self.manager.db.fetchStationEquipmentByModel(ident.model)  # type: ignore[attr-defined]
        if not rec:
            print("No database record for this model on this station (not attached yet).")
            return False

        mismatches: list[str] = []
        if rec.get('manufacturer') != ident.manufacturer:
            mismatches.append(f"manufacturer(db={rec.get('manufacturer')} != dev={ident.manufacturer})")
        if rec.get('model') != ident.model:
            mismatches.append(f"model(db={rec.get('model')} != dev={ident.model})")
        if rec.get('serial') != ident.serial:
            mismatches.append(f"serial(db={rec.get('serial')} != dev={ident.serial})")
        if rec.get('version') != ident.version:
            mismatches.append(f"version(db={rec.get('version')} != dev={ident.version})")
        if not mismatches:
            print(f"Identity OK: {ident}")
        else:
            print("Identity mismatch:")
            for m in mismatches:
                print(f" - {m}")

        return False

    def do_write(self, command):
        """Basic query command to device"""
        if isinstance(self.equip, CommsInterface):
            comms = cast(CommsInterface, self.equip)
            comms.write(command)
            print("Successful")

    def do_query(self, command):
        """Basic query command to device"""
        if isinstance(self.equip, CommsInterface):
            comms = cast(CommsInterface, self.equip)
            resp = comms.query(command)
            if resp is not None:
                print(resp)
            else:
                print("Did not get a response")
