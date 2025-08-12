from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.products.tactical.tactical import Tactical


@hookimpl
@singleton
def createProductPlugin():
    return TacticalU()


class TacticalU(Tactical):
    def __init__(self):
        super().__init__("Tactical_U_Transceiver")

    def Initialise(self) -> bool:
        return super().initialise()
