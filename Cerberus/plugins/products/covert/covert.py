from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import CovertBIST


class BaseCovert(BaseProduct, CovertBIST):
    def __init__(self, name: str, description: str | None = None):
        super().__init__(name, description)


@hookimpl
@singleton
def createProductPlugin():
    return Covert()


class Covert(BaseCovert):
    def __init__(self):
        super().__init__("Covert")

    def Initialise(self) -> bool:
        return super().initialise()
