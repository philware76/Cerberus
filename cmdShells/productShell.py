from testManager import TestManager
from cmdShells.common import displayPluginCategory, getInt
from cmdShells.baseShell import BaseShell
from cmdShells.runCommandShell import RunCommandShell
from plugins.products.baseProduct import BaseProduct


class ProductsShell(BaseShell):
    intro = "Welcome to Cerberus Product System. Type help or ? to list commands.\n"
    prompt = 'Product> '

    def __init__(self, manager: TestManager):
        super().__init__()

        self.manager = manager

    def do_list(self, arg):
        """List all of the Products"""
        displayPluginCategory("Product", self.manager.productPlugins)

    def do_load(self, name):
        """Loads a product"""
        try:
            if idx := getInt(name):
                name = list(self.manager.productPlugins.keys())[idx]
            
            product = self.manager.productPlugins[name]
            
            ProductShell(product).cmdloop()
        except KeyError:
            print(f"Unknown product: {name}")

class ProductShell(RunCommandShell):
    def __init__(self, product:BaseProduct):
        ProductShell.intro = f"Welcome to Cerberus {product.name} Product System. Type help or ? to list commands.\n"
        ProductShell.prompt = f"{product.name}> "

        super().__init__(product)
        self.product: BaseProduct = product
        self.config = {}