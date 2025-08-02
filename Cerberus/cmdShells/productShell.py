from Cerberus.cerberusManager import Manager
from Cerberus.cmdShells.pluginsShell import PluginsShell
from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.plugins.products.baseProduct import BaseProduct


class ProductsShell(PluginsShell):
    def __init__(self, manager:Manager):
        super().__init__(manager, manager.productPlugins, "Product")


class ProductShell(RunCommandShell):
    def __init__(self, product:BaseProduct, manager: Manager):
        ProductShell.intro = f"Welcome to Cerberus {product.name} Product System. Type help or ? to list commands.\n"
        ProductShell.prompt = f"{product.name}> "

        super().__init__(product, manager)
        self.product: BaseProduct = product
        self.config = {}