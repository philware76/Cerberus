from cmdShells.pluginsShell import PluginsShell
from testManager import TestManager
from cmdShells.common import displayPluginCategory, getInt
from cmdShells.baseShell import BaseShell
from cmdShells.runCommandShell import RunCommandShell
from plugins.products.baseProduct import BaseProduct


class ProductsShell(PluginsShell):
    def __init__(self, manager:TestManager):
        super().__init__(manager, manager.productPlugins, "Product")


class ProductShell(RunCommandShell):
    def __init__(self, product:BaseProduct, manager: TestManager):
        ProductShell.intro = f"Welcome to Cerberus {product.name} Product System. Type help or ? to list commands.\n"
        ProductShell.prompt = f"{product.name}> "

        super().__init__(product, manager)
        self.product: BaseProduct = product
        self.config = {}