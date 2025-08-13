from enum import StrEnum


class BandNames(StrEnum):
    LTE7 = 'LTE_7'
    DCS1800 = 'DCS1800'
    PCS1900 = 'PCS1900'
    THREEGBAND1 = 'UMTS_1'
    GSM850 = 'GSM850'
    EGSM900 = 'EGSM900'
    LTE20 = 'LTE_20'
    LTE28A = 'LTE_28A'
    LTE28B = 'LTE_28B'
    LTE28 = 'LTE_28'
    LTE12 = 'LTE_12'
    LTE13 = 'LTE_13'
    LTE17 = 'LTE_17'
    LTE40 = 'LTE_40'
    LTE38 = 'TD_2600'
    LTE41 = 'LTE_41'
    LTE71 = 'LTE_71'
    LTE25 = '1900+'
    LTE26 = '850+'
    N77 = 'LTE_77'
    SPARE1 = 'SPARE1'
    SPARE2 = 'SPARE2'
    SPARE3 = 'SPARE3'
    SPARE4 = 'SPARE4'
    SPARE5 = 'SPARE5'
    OPEN = 'OPEN'

    # Legacy alias names (same values)
    LTE20Rev = 'LTE_20'
    LTE13Rev = 'LTE_13'
    LTE28ARev = 'LTE_28A'


# Bands that have reversed/non-conventional orientation
REVERSED_BANDS: set[BandNames] = {BandNames.LTE20, BandNames.LTE13, BandNames.LTE28A, BandNames.N77}
