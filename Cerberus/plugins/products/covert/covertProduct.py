from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.products.bandNames import *
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import CovertBIST


class BaseCovert(BaseProduct, CovertBIST):
    FILTER_DICT = {
        0x15: LTE7,
        0x16: DCS1800,
        0x17: PCS1900,
        0x18: THREEGBAND1,
        0x19: GSM850,
        0x1A: EGSM900,
        0x1B: LTE20,
        0x2C: LTE12,
        0x2D: LTE13,
        0x36: LTE13Rev,
        0x2E: LTE17,
        0x40: LTE20Rev,
        0x3A: LTE25,
        0x3B: LTE26,
        0x43: LTE28,
        0x1C: LTE28A,
        0x39: LTE28ARev,
        0x1D: LTE28B,
        0x3C: LTE38,
        0x38: LTE40,
        0x3D: LTE41,
        0x3E: LTE71,
        0x3F: n77,
        0x01: OPEN
    }

    SLOT_DETAILS_DICT = {
        0: LTE7, 1: DCS1800, 2: PCS1900, 3: THREEGBAND1, 4: GSM850, 5: EGSM900, 6: LTE20,
        7: SPARE1, 8: SPARE2, 9: SPARE3
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
