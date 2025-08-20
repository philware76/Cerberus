from typing import cast  # added for identity check typing

from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.manager import Manager
from Cerberus.plugins.equipment.baseEquipment import BaseCommsEquipment
from Cerberus.plugins.equipment.commsInterface import CommsInterface
from Cerberus.plugins.equipment.mixins.parentDelegation import \
    SingleParentDelegationMixin
from Cerberus.plugins.equipment.visaDevice import VISADevice


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
        # Direct VISA device
        if isinstance(self.equip, VISADevice):
            try:
                self.equip.getIdentity()
                print(self.equip.identity)

            except Exception as ex:
                print(f"Failed to read identity: {ex}")

            return False

        # Delegated child: try parent if available
        if isinstance(self.equip, SingleParentDelegationMixin) and self.equip.has_parent():
            try:
                parent = self.equip._p()  # type: ignore[attr-defined]
                if isinstance(parent, VISADevice):
                    try:
                        parent.getIdentity()
                    except Exception:
                        pass

                    print(f"(Delegated) Parent '{parent.name}' identity: {getattr(parent, 'identity', 'Unavailable')}")

                else:
                    print("Parent is not a VISA device; no standard identity available.")

            except Exception as ex:
                print(f"Unable to access parent identity: {ex}")

            return False

        print("Equipment is neither a VISADevice nor a delegated child with a VISA parent.")
        return False

    def do_checkId(self, arg):
        """checkId : Compare initialised equipment identity with DB (lookup by model & station)."""
        ident = self.equip.identity
        if not ident or not ident.serial:
            print("Equipment identity/serial unavailable. Is it a VISA device?")
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
        if not command:
            print("Usage: write <SCPI|command>")
            return False

        # Direct communications interface
        if isinstance(self.equip, CommsInterface):
            comms = cast(CommsInterface, self.equip)
            try:
                comms.write(command)
                print("Successful")
            except Exception as ex:
                print(f"Write failed: {ex}")
            return False

        # Delegated (single-parent) comms path
        if isinstance(self.equip, SingleParentDelegationMixin) and self.equip.has_parent():
            try:
                self.equip.write(command)  # type: ignore[call-arg]
                print("Successful (delegated)")
            except Exception as ex:
                print(f"Delegated write failed: {ex}")
            return False

        print("This equipment does not support write() (no comms interface / parent not attached).")
        return False

    def do_query(self, command):
        """Basic query command to device"""
        if not command:
            print("Usage: query <SCPI|command>")
            return False

        # Direct communications interface
        if isinstance(self.equip, CommsInterface):
            comms = cast(CommsInterface, self.equip)
            try:
                resp = comms.query(command)
                if resp is not None:
                    print(resp)

                else:
                    print("Did not get a response")

            except Exception as ex:
                print(f"Query failed: {ex}")

            return False

        # Delegated (single-parent) comms path
        if isinstance(self.equip, SingleParentDelegationMixin) and self.equip.has_parent():
            try:
                resp = self.equip.query(command)  # type: ignore[call-arg]
                if resp is not None:
                    print(resp)

                else:
                    print("Did not get a response (delegated)")

            except Exception as ex:
                print(f"Delegated query failed: {ex}")

            return False

        print("This equipment does not support query() (no comms interface / parent not attached).")
        return False

    def do_saveSettings(self, arg):
        """Save the settings to the database"""
        db = self.manager.db
        db.save_equipment([self.plugin])
    # ---------------- Parent delegation utilities ---------------------------------

    def do_getParent(self, arg):  # child perspective
        """getParent : Attach the declared REQUIRED_PARENT automatically.

        If a parent is already attached, shows its name. If the equipment
        declares REQUIRED_PARENT and the parent exists (and is initialised /
        can be initialised) it is attached. Otherwise an error is printed.
        """
        equip = self.equip
        if not isinstance(equip, SingleParentDelegationMixin):
            print("This equipment does not support parent delegation.")
            return False

        if equip.has_parent():
            try:
                parent = equip._p()  # type: ignore[attr-defined]
                print(f"Parent already attached: {parent.name}")

            except Exception:
                print("Parent attached but inaccessible (internal error).")

            return False

        required = equip.parent_name_required()
        if not required:
            print("No REQUIRED_PARENT declared.")
            return False

        from Cerberus.pluginService import PluginService
        ps = PluginService.instance()
        if ps is None:
            print("PluginService instance not available.")
            return False

        parent = ps.findEquipment(required)
        if parent is None:
            print(f"Required parent '{required}' not found among discovered equipment.")
            return False

        try:
            parent.initialise()

        except Exception as ex:
            print(f"Failed to initialise parent '{parent.name}': {ex}")
            return False

        try:
            equip.attach_parent(parent)  # type: ignore[arg-type]
            print(f"Attached parent '{parent.name}'.")

        except Exception as ex:
            print(f"Failed to attach parent: {ex}")

        return False

    def do_setParentEquip(self, childName):  # parent perspective
        """setParentEquip <childName> : Attach this equipment as parent of the named child.

        Validates that the child declares this equipment in REQUIRED_PARENT
        before attaching.
        """
        if not childName:
            print("Usage: setParentEquip <childEquipmentName>")
            return False

        from Cerberus.pluginService import PluginService
        ps = PluginService.instance()
        if ps is None:
            print("PluginService instance not available.")
            return False

        child = ps.findEquipment(childName)
        if child is None:
            print(f"Child equipment '{childName}' not found.")
            return False

        if not isinstance(child, SingleParentDelegationMixin):
            print(f"Child '{childName}' does not support parent delegation.")
            return False

        required = child.parent_name_required()
        if required and required != self.equip.name:
            print(f"Child requires parent '{required}', not '{self.equip.name}'.")
            return False

        try:
            # Ensure this (parent) is initialised first
            self.equip.initialise()

        except Exception as ex:
            print(f"Failed to initialise parent '{self.equip.name}': {ex}")
            return False

        try:
            child.attach_parent(self.equip)  # type: ignore[arg-type]
            print(f"Attached '{self.equip.name}' as parent of '{child.name}'.")

        except Exception as ex:
            print(f"Failed to attach: {ex}")

        return False

    def do_detachParent(self, arg):
        """detachParent : Detach currently attached parent (if any)."""
        equip = self.equip
        if not isinstance(equip, SingleParentDelegationMixin):
            print("This equipment does not support parent delegation.")
            return False

        if not equip.has_parent():
            print("No parent attached.")
            return False

        try:
            equip.detach_parent()
            print("Parent detached.")

        except Exception as ex:
            print(f"Failed to detach parent: {ex}")

        return False
