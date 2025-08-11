from tabulate import tabulate

from Cerberus.cmdShells.common import is_valid_ip
from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.ethDiscovery import EthDiscovery
from Cerberus.manager import Manager
from Cerberus.plugins.products.baseProduct import BaseProduct


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
        self.nesies = {}
        self.nesieIP: str | None = None

    def do_discover(self, arg):
        """Discovery NESIE devices on the network.
        You can specify the Key to sort on too."""
        if arg is not None and arg != "":
            sortField = arg
        else:
            sortField = "ID"

        self.nesies = EthDiscovery().search()
        if self.nesies is not None and len(self.nesies) > 0:
            self.nesies = sorted(self.nesies, key=lambda x: x[sortField])
            print(tabulate(self.nesies, headers="keys", tablefmt="pretty"))
        else:
            print("No devices found!")

    def do_select(self, arg):
        """Select a device to use"""
        if arg is None or arg == "":
            print("You need to specify the IP Address of the device to select")
            return

        if not is_valid_ip(arg):
            print("You must use a valid IP Address format")
            return

        matches = [d for d in self.nesies if d["IP Address"] == arg]
        if len(matches) == 0:
            print(f"Device at IP Address '{arg}' is not available. Run discover again.")
            return

        self.nesieIP = matches[0]
        print(f"Selected device: {self.nesieIP}")
