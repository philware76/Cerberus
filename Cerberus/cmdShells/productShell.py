import shlex
from pathlib import Path
from typing import Dict, List, cast

from tabulate import tabulate

from Cerberus.cmdShells.common import is_valid_ip
from Cerberus.cmdShells.picShell import PICShell
from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.ethDiscovery import EthDiscovery
from Cerberus.manager import Manager
from Cerberus.plugins.common import NESIE_TYPES
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import BaseBIST
from Cerberus.plugins.products.utilities import (EEPROM, FittedBands, NesieSSH,
                                                 SSHComms)


class ProductsShell(PluginsShell):
    def __init__(self, manager: Manager):
        pluginService = manager.pluginService
        super().__init__(manager, pluginService.productPlugins, "Product")

        self.picIPAddress: str | None = None
        self.nesies: List[Dict[str, str]] = []

    def do_discover(self, arg):
        """Discover NESIE devices.
        Usage:
          - discover                         -> no filter, no sort
          - discover <sortColumn>            -> sort by column
          - discover <filterColumn> <value>  -> filter on column (contains, case-insensitive), then sort by Name
        Examples:
          - discover ID
          - discover ID K
        """
        parts = shlex.split(arg) if arg else []
        filter_col = None
        filter_value = None
        sort_field = None

        if len(parts) == 0:
            sort_field = "Name"  # default sort when no args
        elif len(parts) == 1:
            sort_field = parts[0]
        elif len(parts) >= 2:
            filter_col, filter_value = parts[0], parts[1]
            sort_field = "Name"  # default sort after filtering

        devices = EthDiscovery.search()
        if not devices:
            print("No devices found!")
            self.nesies = []
            return

        # Build case-insensitive key map for columns
        key_map = {k.casefold(): k for k in devices[0].keys()}

        # Apply filter if requested (case-insensitive column and value)
        if filter_col and filter_value:
            norm_filter_col = key_map.get(filter_col.casefold())
            if not norm_filter_col:
                print(f"Unknown filter column '{filter_col}'. Available: {', '.join(devices[0].keys())}")
                self.nesies = []
                return
            fv = str(filter_value).casefold()

            def _contains(v):
                try:
                    return fv in str(v).casefold()
                except Exception:
                    return False
            devices = [d for d in devices if _contains(d.get(norm_filter_col, ""))]
            if not devices:
                print("No devices match the specified filter.")
                self.nesies = []
                return

        # Optional sort (case-insensitive column name)
        if sort_field:
            norm_sort_field = key_map.get(sort_field.casefold())
            if norm_sort_field:
                devices = sorted(devices, key=lambda x: x[norm_sort_field])
            else:
                print(f"Unknown sort field '{sort_field}'. No sorting applied.")

        # Reindex and place Idx first
        self.nesies = [{"Idx": str(i), **nesie} for i, nesie in enumerate(devices)]
        print(tabulate(self.nesies, headers="keys", tablefmt="pretty"))

    def _select(self, arg) -> bool:
        if len(self.nesies) == 0:
            print("Please run discover before selecting a Nesie")
            return False

        if not is_valid_ip(arg):
            if not arg.isdigit():
                print("You must use a valid Index or IP Address format")
                return False

            else:
                selected = self.nesies[int(arg)]

        else:
            matches = [d for d in self.nesies if d["IP Address"] == arg]
            if len(matches) == 0:
                print(f"Device at IP Address '{arg}' is not available. Run discover again.")
                return False

            selected = matches[0]

        self.picIPAddress = selected["IP Address"]
        self.productType = selected['Type']
        self.productID = selected['ID']
        # ProductsShell.prompt = f"{self.productType} @{self.picIPAddress}> "

        return True

    def do_connect(self, arg):
        """Connects the selected device to a Product Plugin. Can select with Connect <IP | Idx> as well"""
        if arg is None:
            print("You must provide an IP address or Index to connect to")
            return

        if not self._select(arg):
            return

        productPluginName = NESIE_TYPES[self.productID]
        super().do_load(productPluginName)
        if self._shell is not None:
            pShell = cast(ProductShell, self._shell)
            pShell.picIPAddress = self.picIPAddress
            ProductShell.prompt = f"{productPluginName} @{pShell.picIPAddress}> "

        super().do_open("")

    def do_load(self, name):
        """Do not use for Product shell"""
        super().do_load(name)

    def do_open(self, arg):
        """Do not use for Product shell"""
        print("Please use 'discover' and then 'connect'")


class ProductShell(RunCommandShell):
    def __init__(self, product: BaseProduct, manager: Manager):
        ProductShell.intro = f"""
            Welcome to Cerberus {product.name} Product System. Type help or ? to list commands.
            Please use openPIC or openDA commands first\n
            """

        super().__init__(product, manager)
        self.product: BaseProduct = product
        self.config = {}
        self.nesies: List[Dict[str, str]] = []
        self.picIPAddress: str | None = None
        self.daIPAddress: str | None = None
        self.bist: BaseBIST | None = None
        self._eeprom_values: list[str] = []

    def do_openPIC(self, arg):
        """Open the PIC controller"""
        if self.picIPAddress is None:
            print("No selected PIC to open")
            return

        picShell = PICShell(self.manager, self.product.name, self.picIPAddress)
        self.daIPAddress = picShell.runLoop()
        ProductShell.prompt = f"{self.product.name} @{self.picIPAddress}> "

    def do_openDA(self, arg):
        """Connect to a Nesie with the selected IP """
        host = self._require_da_ip()
        if not host:
            return

        # if it's the same connection, don't do anything
        if self.bist is not None and self.bist.bistHost == host:
            ProductShell.prompt = f"{self.product.name} DA@{host}> "
            return

        # If we have got a bist, and it's not the same as before, close the previous connection
        if self.bist is not None:
            print("Closing previous BIST connection...")
            self.bist.closeBIST()

        # Now open a new BIST telnet connection
        self.bist = cast(BaseBIST, self.product)
        self.bist.initComms(host=host)
        self.bist.openBIST()

        ProductShell.prompt = f"{self.product.name} DA@{host}> "

    def _resolve_key_path(self) -> Path:
        # From cmdShells/productShell.py -> up to Cerberus, down to plugins/products/Keys/id_rsa.zynq
        return (Path(__file__).resolve().parent.parent / "plugins" / "products" / "Keys" / "id_rsa.zynq").resolve()

    def _require_da_ip(self) -> str | None:
        if self.daIPAddress is None:
            print("Please use openPIC command first to get DA Address")
            return None

        if self.daIPAddress == "0.0.0.0":
            print("Device has not yet booted. Please boot device first using openPIC/powerON commands")
            return None
        return self.daIPAddress

    def do_stopNesie(self, arg):
        """Stop the NESIE daemon on the DA via SSH."""
        host = self._require_da_ip()
        if not host:
            return

        key_path = self._resolve_key_path()
        with SSHComms(host, username="root", key_path=key_path) as ssh:
            nesie = NesieSSH(ssh)
            ok = nesie.stop_daemon()
            print("NESIE-daemon stopped" if ok else "Failed to stop NESIE-daemon")

    def do_killNesie(self, arg):
        """Kill the NESIE daemon process on the DA via SSH."""
        host = self._require_da_ip()
        if not host:
            return

        key_path = self._resolve_key_path()
        with SSHComms(host, username="root", key_path=key_path) as ssh:
            nesie = NesieSSH(ssh)
            ok, _ = nesie.kill_nesie()
            print("killall nesie-daemon sent" if ok else "Failed to issue killall nesie-daemon")

    def do_readEEPROM(self, arg):
        """Read EEPROM contents from the DA via SSH."""
        host = self._require_da_ip()
        if not host:
            return

        key_path = self._resolve_key_path()
        with SSHComms(host, username="root", key_path=key_path) as ssh:
            eep = EEPROM(ssh)
            values = eep.read()
            self._eeprom_values = values or []

            if values:
                # Pretty print as rows of 8 words
                row = 8
                print("EEPROM 32-bit values ({} total):".format(len(values)))
                for i in range(0, len(values), row):
                    chunk = values[i:i+row]
                    print("  " + "  ".join(chunk))
            else:
                print("Failed to read EEPROM or no data parsed")

    def do_bandsFitted(self, arg):
        """Show fitted bands from the last EEPROM read.
        Usage: bandsFitted
        Note: Run readEEPROM first.
        """
        if not self._eeprom_values:
            print("No EEPROM data cached. Run readEEPROM first.")
            return

        slot_details = self.product.SLOT_DETAILS_DICT
        filter_dict = self.product.FILTER_DICT
        if not slot_details or not filter_dict:
            print("Product does not provide SLOT_DETAILS_DICT and FILTER_DICT")
            return

        bands = FittedBands.bands(self._eeprom_values, slot_details, filter_dict)
        if not bands:
            print("No fitted bands could be determined")
            return

        print(f"Fitted bands ({len(bands)}):")
        for i, name in enumerate(bands, 1):
            print(f"  {i:2d}. {name}")

    def do_slotDetails(self, arg):
        """Pretty-print the product's SLOT_DETAILS_DICT mapping of slot -> band name.
        Usage: slotDetails
        """
        slot_details = self.product.SLOT_DETAILS_DICT
        if not slot_details:
            print("Product does not provide SLOT_DETAILS_DICT")
            return

        print(f"Slot details ({len(slot_details)}):")
        for idx in sorted(slot_details.keys()):
            print(f"  Slot {idx:2d}: {slot_details[idx]}")
