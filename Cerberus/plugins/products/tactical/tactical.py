from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import TacticalBIST


class Tactical(BaseProduct, TacticalBIST):
    def __init__(self, name: str, description: str | None = None):
        super().__init__(name, description)
