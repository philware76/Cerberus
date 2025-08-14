import logging
import time
from dataclasses import asdict
from typing import cast

from Cerberus.common import dwell
from Cerberus.exceptions import EquipmentError
from Cerberus.plugins.baseParameters import (BaseParameters, NumericParameter,
                                             OptionParameter)
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.chambers.baseChamber import BaseChamber
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
    BaseSpecAnalyser
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.products.bandNames import BandNames, RxFilterMapping
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.products.bist import TacticalBISTCmds
from Cerberus.plugins.products.nesieFirmware import nesie_rx_filter_bands
from Cerberus.plugins.products.tactical.tactical import BaseTactical
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import BaseTestResult, ResultStatus


@hookimpl
@singleton
def createTestPlugin():
    return TxLevelTest()


class TxLevelTestResult(BaseTestResult):
    def __init__(self, status):
        super().__init__("TxLevelTest", status)


class TxLevelTestParameters(BaseParameters):
    def __init__(self, ):
        super().__init__("RF Parameters")

        self.addParameter(NumericParameter("Tx Level", 0.0, units="dBm", minValue=-30, maxValue=+23, description="Sets the Transmit power level"))
        self.addParameter(NumericParameter("Start", -10.5, units="dBm", minValue=0, maxValue=25, description="Sets the Transmit power level"))
        self.addParameter(OptionParameter("Enable Tx PA", True))


class TxLevelTest(BaseTest):
    AD9361_DC_NOTCH_FREQ_OFFSET = 1  # MHz

    def __init__(self):
        super().__init__("Tx Level")
        self._addRequirements([BaseChamber, BaseSpecAnalyser, BaseSigGen])
        self.addParameterGroup(TxLevelTestParameters())

        self.bist: TacticalBISTCmds
        self.freqOffset = TxLevelTest.AD9361_DC_NOTCH_FREQ_OFFSET
        self.specAna: BaseSpecAnalyser

    def run(self):
        super().run()

        self.configSpecAna()
        self.initProduct()

        # iterate through the bands fitted
        for hwId, bandName in self.product.getBands():
            logging.debug(f"Testing on Band {bandName}")
            self.testBand(hwId, bandName)

        self.result = TxLevelTestResult(ResultStatus.PASSED)

    def testBand(self, hwId: int, bandName: BandNames):

        self.configProductForFreq(hwId, bandName)
        self.bist.set_attn(25)

        time.sleep(0.5)

        measuredPwr = self.specAna.getMarker()
        detectedPwr = self.bist.get_pa_pwr()

        time.sleep(2)

    def configProductForFreq(self, hwId: int, bandName: BandNames):
        """Configures the product for a particular band"""
        self.filt = nesie_rx_filter_bands.RX_FILTER_BANDS_BY_ID[hwId]
        filt_dict = asdict(self.filt)
        logging.debug("RxFilterBand: hw_id=%s band=%s", self.filt.hardware_id, self.filt.band.name)
        for k, v in filt_dict.items():
            logging.debug("  %s = %r", k, v)

        # set duplexer
        self.bist.set_duplexer(bandName, "TX")

        # set the forward/reverse
        if self.filt.extra_data & nesie_rx_filter_bands.EXTRA_DATA_SWAP_FOR_AND_REV_MASK:
            self.bist.set_tx_fwd_rev("CLEAR")
        else:
            self.bist.set_tx_fwd_rev("SET")

        self.bist.set_tx_bw(5)
        self.bist.set_ts_freq(self.freqOffset)
        self.bist.set_ts_enable()

    def initProduct(self):
        self.product = self.getProduct()
        self.product.readFittedBands()

        self.product.openBIST()
        self.bist = cast(TacticalBISTCmds, self.product)
        self.bist.set_attn(BaseTactical.MAX_ATTENUATION)
        self.bist.set_tx_enable()
        self.bist.set_tx_bw(5)
        self.bist.set_ts_enable()
        self.bist.set_ts_freq(self.freqOffset)

        dwell(0.5)

    def configSpecAna(self):
        self.specAna = self.getEquip(BaseSpecAnalyser)
        cast(VISADevice, self.specAna).reset()

        self.specAna.setRefInput("EXT")
        self.specAna.setSpan(1)
        self.specAna.setBWS("NUTT")
        self.specAna.setRBW(10)
        self.specAna.setVBW(10)
        self.specAna.setRefLevel(20)
