from typing import cast  # added for identity check typing

from Cerberus.cmdShells.baseCommsShell import BaseCommsShell
from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.common import camel2Human
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

    def do_listCommParams(self, arg):
        """listCommParams : List all equipment with their communication parameters (IP, Port, etc.)."""
        from Cerberus.pluginService import PluginService
        ps = PluginService.instance()
        if ps is None:
            print("PluginService instance not available.")
            return False

        # Separate equipment into two categories
        comm_equipment = []
        no_comm_equipment = []
        error_equipment = []

        # Get all equipment from the plugin service
        for name, equipment in ps.equipPlugins.items():
            try:
                # Try to get the Communication parameters group
                comm_params = equipment.getGroupParameters("Communication")

                # Extract the communication parameters
                ip_param = comm_params.get("IP Address")
                port_param = comm_params.get("Port")
                timeout_param = comm_params.get("Timeout")

                ip_address = ip_param.value if ip_param else "N/A"
                port = port_param.value if port_param else "N/A"
                timeout = timeout_param.value if timeout_param else "N/A"

                # Determine the base equipment type
                base_type = self._get_base_equipment_type(equipment)

                comm_equipment.append((name, ip_address, port, timeout, base_type))

            except ValueError:
                # Equipment doesn't have Communication parameters group
                no_comm_equipment.append(name)
            except Exception as ex:
                error_equipment.append((name, str(ex)))

        # Sort communication equipment by Equipment Type
        comm_equipment.sort(key=lambda item: item[4])  # Sort by base_type (index 4)

        # Print equipment with communication parameters
        if comm_equipment:
            print("\nEquipment with Communication Parameters:")
            print("=" * 85)
            print(f"{'Equipment Name':<20} {'IP Address':<15} {'Port':<8} {'Timeout':<10} {'Equipment Type':<18}")
            print("-" * 85)

            for name, ip_address, port, timeout, base_type in comm_equipment:
                print(f"{name:<20} {ip_address:<15} {str(port):<8} {str(timeout):<10} {base_type:<18}")

            print("-" * 85)

        # Print equipment without communication parameters
        if no_comm_equipment:
            print(f"\nEquipment without Communication Parameters ({len(no_comm_equipment)}):")
            print("=" * 40)
            for name in no_comm_equipment:
                print(f"  {name}")
            print("=" * 40)

        # Print equipment with errors (if any)
        if error_equipment:
            print(f"\nEquipment with Errors ({len(error_equipment)}):")
            print("=" * 50)
            for name, error in error_equipment:
                print(f"  {name}: {error}")
            print("=" * 50)

        return False

    def _get_base_equipment_type(self, equipment):
        """Determine the base equipment type from the class hierarchy."""
        # Import the base classes to check against
        from Cerberus.plugins.equipment.baseEquipment import (
            BaseCommsEquipment, BaseEquipment)
        from Cerberus.plugins.equipment.cables.baseCalCable import BaseCalCable
        from Cerberus.plugins.equipment.chambers.baseChamber import BaseChamber
        from Cerberus.plugins.equipment.powerMeters.basePowerMeters import \
            BasePowerMeter
        from Cerberus.plugins.equipment.signalGenerators.baseSigGen import \
            BaseSigGen
        from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
            BaseSpecAnalyser

        # Check for specific base types (most specific first)
        if isinstance(equipment, BaseSpecAnalyser):
            return self._format_equipment_type("SpecAnalyser")
        elif isinstance(equipment, BaseSigGen):
            return self._format_equipment_type("SigGen")
        elif isinstance(equipment, BasePowerMeter):
            return self._format_equipment_type("PowerMeter")
        elif isinstance(equipment, BaseChamber):
            return self._format_equipment_type("Chamber")
        elif isinstance(equipment, BaseCalCable):
            return self._format_equipment_type("CalCable")
        elif isinstance(equipment, BaseCommsEquipment):
            return self._format_equipment_type("CommsEquipment")
        elif isinstance(equipment, BaseEquipment):
            return self._format_equipment_type("Equipment")
        else:
            return "Unknown"

    def _format_equipment_type(self, type_name):
        """Format equipment type name using camel2Human for better readability."""
        return camel2Human(type_name)


class EquipmentShell(BaseCommsShell):
    def __init__(self, equip: BaseCommsEquipment, manager: Manager):
        EquipmentShell.intro = f"Welcome to Cerberus {equip.name} Equipment shell. Type help or ? to list commands.\n"
        EquipmentShell.prompt = f"{equip.name}> "

        super().__init__(equip, manager)
        self.equip: BaseCommsEquipment = equip
        self.config = {}

    # do_identity inherited from BaseCommsShell

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

    # do_write inherited from BaseCommsShell

    # do_query inherited from BaseCommsShell

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

        # After successful initialisation, show already-fetched identity (do not re-query)
        ident_str = None
        if isinstance(parent, VISADevice):
            ident_obj = getattr(parent, 'identity', None)
            if ident_obj:
                ident_str = str(ident_obj)

        if ident_str:
            print(f"Initialised parent '{parent.name}' identity: {ident_str}")
        else:
            print(f"Initialised parent '{parent.name}'.")

        try:
            equip.attach_parent(parent)  # type: ignore[arg-type]
            # Update prompt to Parent/Child form
            EquipmentShell.prompt = f"{parent.name}/{equip.name}> "
            print(f"Attached parent '{parent.name}' (delegation enabled).")
            # refresh comms adapter (child now has delegated path)
            self._refresh_comms()

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
            # If we attached ourselves as a parent, ensure our own comms (if child view) refreshed
            self._refresh_comms()

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
            self._refresh_comms()
            # Indicate parent currently absent
            EquipmentShell.prompt = f"Parent?/{equip.name}> "

        except Exception as ex:
            print(f"Failed to detach parent: {ex}")

        return False

    # Auto-attempt parent attachment when shell loop starts (only once per open)
    def preloop(self):
        super().preloop()
        equip = self.equip
        if isinstance(equip, SingleParentDelegationMixin):
            if not equip.has_parent() and equip.parent_name_required():
                # Run getParent logic (prints outcome). User can rerun manually if needed.
                self.do_getParent("")
