from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.products.tactical.tactical import Tactical


@hookimpl
@singleton
def createProductPlugin():
    return TacticalG()


class TacticalG(Tactical):
    def __init__(self):
        super().__init__("Tactical_G_Transceiver")

    def Initialise(self) -> bool:
        return super().initialise()
