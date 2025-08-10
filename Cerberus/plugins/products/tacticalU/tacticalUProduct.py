import logging

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.products.baseProduct import BaseProduct


@hookimpl
@singleton
def createProductPlugin():
    return TacticalU()


class TacticalU(BaseProduct):
    def __init__(self):
        super().__init__("Tactical-U")

    def Initialise(self) -> bool:
        return super().initialise()
