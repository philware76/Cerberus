from Cerberus.plugins.products.bandNames import *
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import TacticalBIST


class BaseTactical(BaseProduct, TacticalBIST):
    FILTER_DICT = {
        0x2F: LTE7,
        0x30: LTE20,
        0x31: GSM850,
        0x32: EGSM900,
        0x33: DCS1800,
        0x34: PCS1900,
        0x35: THREEGBAND1,
        0x2C: LTE12,
        0x2D: LTE13,
        0x36: LTE13Rev,
        0x2E: LTE17,
        0x41: LTE20Rev,
        0x3A: LTE25,
        0x3B: LTE26,
        0x39: LTE28ARev,
        0x43: LTE28,
        0x1C: LTE28A,
        0x1D: LTE28B,
        0x3C: LTE38,
        0x37: LTE40,
        0x3D: LTE41,
        0x3E: LTE71,
        0x3F: n77
    }

    SLOT_DETAILS_DICT = {
        0: LTE7, 1: LTE20, 2: GSM850, 3: EGSM900, 4: DCS1800, 5: PCS1900, 6: THREEGBAND1,
        7: SPARE1, 8: SPARE2, 9: SPARE3, 10: SPARE4, 11: SPARE5
    }

    def __init__(self, name: str, description: str | None = None):
        super().__init__(name, description)
