from typing import Dict, List

from tabulate import tabulate

from Cerberus.cmdShells.common import is_valid_ip
from Cerberus.cmdShells.picShell import PICShell
from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.ethDiscovery import EthDiscovery
from Cerberus.manager import Manager
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.nesiePIC import NesiePIC


class ProductsShell(PluginsShell):
    def __init__(self, manager: Manager):
        pluginService = manager.pluginService
        super().__init__(manager, pluginService.productPlugins, "Product")


class ProductShell(RunCommandShell):
    def __init__(self, product: BaseProduct, manager: Manager):
        ProductShell.intro = f"Welcome to Cerberus {product.name} Product System. Type help or ? to list commands.\n"
        ProductShell.prompt = f"{product.name}> "

        super().__init__(product, manager)
        self.product: BaseProduct = product
        self.config = {}
        self.nesies: List[Dict[str, str]] = []
        self.picIPAddress: str | None = None
        self.daIPAddress: str | None = None

    def do_discover(self, arg):
        """Discovery NESIE devices on the network.
        You can specify the Key to sort on too."""
        if arg is not None and arg != "":
            sortField = arg
        else:
            sortField = "Name"

        self.nesies = EthDiscovery().search()
        if self.nesies is not None and len(self.nesies) > 0:
            # Sort first on requested field (if present in original records)
            if sortField in self.nesies[0]:
                self.nesies = sorted(self.nesies, key=lambda x: x[sortField])

            self.nesies = [{"Idx": str(i), **nesie} for i, nesie in enumerate(self.nesies)]
            print(tabulate(self.nesies, headers="keys", tablefmt="pretty"))
        else:
            print("No devices found!")

    def do_select(self, arg):
        """Select a device to use"""
        if arg is None or arg == "":
            print("You need to specify the IP Address of the device to select")
            return

        if len(self.nesies) == 0:
            print("Please run discover before selecting a Nesie")
            return

        if not is_valid_ip(arg):
            if not arg.isdigit():
                print("You must use a valid Index or IP Address format")
                return
            else:
                selected = self.nesies[int(arg)]
        else:
            matches = [d for d in self.nesies if d["IP Address"] == arg]
            if len(matches) == 0:
                print(f"Device at IP Address '{arg}' is not available. Run discover again.")
                return

            selected = matches[0]

        self.picIPAddress = selected["IP Address"]
        ProductShell.prompt = f"{self.product.name} PIC@{self.picIPAddress}> "

    def do_openPIC(self, arg):
        """Open the PIC to get the status and to power on/off"""
        if self.picIPAddress is None or self.picIPAddress == "":
            self.do_select(arg)

        if self.picIPAddress is None:
            print("No selected PIC to open")
            return

        picShell = PICShell(self.manager, self.product.name, self.picIPAddress)
        self.daIPAddress = picShell.runLoop()
        ProductShell.prompt = f"{self.product.name} PIC@{self.picIPAddress}> "

    def do_connectDA(self, arg):
        """Connect to a Nesie with the selected IP """
        if self.daIPAddress is None or self.daIPAddress == "0.0.0.0":
            print("Device has not yet booted. Please boot device first using openPIC/powerON commands")
            return

        self.product.initComms(host=self.daIPAddress)
        self.product.openBIST()
        ProductShell.prompt = f"{self.product.name} DA@{self.daIPAddress}> "
