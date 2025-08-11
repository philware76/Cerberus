from Cerberus.plugins.products.baseProduct import BaseProduct


class Tactical(BaseProduct):
    def __init__(self, name: str, description: str | None = None):
        super().__init__(name, description)
