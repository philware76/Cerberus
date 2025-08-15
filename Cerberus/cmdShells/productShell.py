import shlex
from pathlib import Path
from typing import cast

from tabulate import tabulate

from Cerberus.cmdShells.common import is_valid_ip
from Cerberus.cmdShells.picShell import PICShell
from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.ethDiscovery import EthDiscovery
from Cerberus.manager import Manager
from Cerberus.plugins.common import PROD_ID_MAPPING
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import BaseBIST
from Cerberus.plugins.products.eeprom import EEPROM, FittedBands
from Cerberus.plugins.products.nesieSSH import NesieSSH
from Cerberus.plugins.products.sshComms import SSHComms


class ProductsShell(PluginsShell):
    def __init__(self, manager: Manager):
        pluginService = manager.pluginService
        super().__init__(manager, pluginService.productPlugins, "Product")

        self.picIPAddress: str | None = None
        self.nesies: list[dict[str, str]] = []

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

        productPluginName = PROD_ID_MAPPING[self.productID]
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

        self.picIPAddress: str | None = None
        self.daIPAddress: str | None = None
        self.bist: BaseBIST | None = None
        self.eeprom: list[str] = []

    def do_select(self, arg):
        """Select this product as the Device Under Test (DUT)"""
        self.manager.product = self.product
        print(f"\n{self.product.name} is selected for test\n")

    def do_openPIC(self, arg):
        """Open the PIC controller"""
        if self.picIPAddress is None:
            print("No selected PIC to open")
            return

        picShell = PICShell(self.manager, self.product.name, self.picIPAddress)
        daHost = picShell.runLoop()
        self.daIPAddress = daHost
        self.product.setDAHost(daHost)

        ProductShell.prompt = f"{self.product.name} @{self.picIPAddress}> "

    def do_openDA(self, arg):
        """Connect to a Nesie with the selected IP """
        if self.product.isBISTOpen():
            print("Closing previous BIST connection...")
            self.product.closeBIST()

        host = self.product.openBIST()

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

    def do_getBandsFitted(self, arg):
        """Read the EEPROM and get the fitted bands"""
        self.product.readFittedBands()
        bands = self.product.getBands()
        print(f"Fitted bands ({len(bands)}):")
        for i, band in enumerate(bands, 1):
            print(f"  {i:2d}. {band}")

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
