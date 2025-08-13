from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.products.bandNames import BandNames
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import StrategicBIST


class BaseStrategic(BaseProduct, StrategicBIST):
    SLOT_DETAILS_DICT = {0: BandNames.EGSM900, 1: BandNames.DCS1800, 2: BandNames.THREEGBAND1}

    def __init__(self, name: str, description: str | None = None):
        super().__init__(name, description)


@hookimpl
@singleton
def createProductPlugin():
    return Strategic()


class Strategic(BaseStrategic):
    def __init__(self):
        super().__init__("Strategic")

    def Initialise(self) -> bool:
        return super().initialise()
