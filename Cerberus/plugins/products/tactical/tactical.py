from Cerberus.plugins.products.bandNames import BandNames
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import TacticalBISTCmds


class BaseTactical(BaseProduct, TacticalBISTCmds):
    FILTER_DICT = {
        0x2F: BandNames.LTE7,
        0x30: BandNames.LTE20,
        0x31: BandNames.GSM850,
        0x32: BandNames.EGSM900,
        0x33: BandNames.DCS1800,
        0x34: BandNames.PCS1900,
        0x35: BandNames.THREEGBAND1,
        0x2C: BandNames.LTE12,
        0x2D: BandNames.LTE13,
        0x36: BandNames.LTE13Rev,
        0x2E: BandNames.LTE17,
        0x41: BandNames.LTE20Rev,
        0x3A: BandNames.LTE25,
        0x3B: BandNames.LTE26,
        0x39: BandNames.LTE28ARev,
        0x43: BandNames.LTE28,
        0x1C: BandNames.LTE28A,
        0x1D: BandNames.LTE28B,
        0x3C: BandNames.LTE38,
        0x37: BandNames.LTE40,
        0x3D: BandNames.LTE41,
        0x3E: BandNames.LTE71,
        0x3F: BandNames.N77,
    }

    SLOT_DETAILS_DICT = {
        0: BandNames.LTE7, 1: BandNames.LTE20, 2: BandNames.GSM850, 3: BandNames.EGSM900, 4: BandNames.DCS1800, 5: BandNames.PCS1900, 6: BandNames.THREEGBAND1,
        7: BandNames.SPARE1, 8: BandNames.SPARE2, 9: BandNames.SPARE3, 10: BandNames.SPARE4, 11: BandNames.SPARE5,
    }

    MAX_ATTENUATION = 89.75

    def __init__(self, name: str, description: str | None = None):
        super().__init__(name, description)
