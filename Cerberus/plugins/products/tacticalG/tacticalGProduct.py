import logging

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.products.baseProduct import BaseProduct


@hookimpl
@singleton
def createProductPlugin():
    return TacticalG()

class TacticalG(BaseProduct):
    def __init__(self):
        super().__init__("Tactical-G")

    def Initialise(self) -> bool:
        return super().Initialise()
    
    def isInitialised(self) -> bool:
        return super().isInitialised()