from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.products.bandNames import BandNames
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import CovertBIST


class BaseCovert(BaseProduct, CovertBIST):
    FILTER_DICT = {
        0x15: BandNames.LTE7,
        0x16: BandNames.DCS1800,
        0x17: BandNames.PCS1900,
        0x18: BandNames.THREEGBAND1,
        0x19: BandNames.GSM850,
        0x1A: BandNames.EGSM900,
        0x1B: BandNames.LTE20,
        0x2C: BandNames.LTE12,
        0x2D: BandNames.LTE13,
        0x36: BandNames.LTE13Rev,
        0x2E: BandNames.LTE17,
        0x40: BandNames.LTE20Rev,
        0x3A: BandNames.LTE25,
        0x3B: BandNames.LTE26,
        0x43: BandNames.LTE28,
        0x1C: BandNames.LTE28A,
        0x39: BandNames.LTE28ARev,
        0x1D: BandNames.LTE28B,
        0x3C: BandNames.LTE38,
        0x38: BandNames.LTE40,
        0x3D: BandNames.LTE41,
        0x3E: BandNames.LTE71,
        0x3F: BandNames.N77,
        0x01: BandNames.OPEN,
    }

    SLOT_DETAILS_DICT = {
        0: BandNames.LTE7, 1: BandNames.DCS1800, 2: BandNames.PCS1900, 3: BandNames.THREEGBAND1, 4: BandNames.GSM850, 5: BandNames.EGSM900, 6: BandNames.LTE20,
        7: BandNames.SPARE1, 8: BandNames.SPARE2, 9: BandNames.SPARE3,
    }

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
