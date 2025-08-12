from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.products.bandNames import *
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import StrategicBIST


class BaseStrategic(BaseProduct, StrategicBIST):
    def __init__(self, name: str, description: str | None = None):
        super().__init__(name, description)


SLOT_DETAILS_DICT = {0: EGSM900, 1: DCS1800, 2: THREEGBAND1}


@hookimpl
@singleton
def createProductPlugin():
    return Strategic()


class Strategic(BaseStrategic):
    def __init__(self):
        super().__init__("Strategic")

    def Initialise(self) -> bool:
        return super().initialise()
        return super().initialise()
