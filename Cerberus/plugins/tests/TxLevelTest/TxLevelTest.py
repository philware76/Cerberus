import logging
import time
from dataclasses import asdict
from typing import cast

from Cerberus.common import dwell
from Cerberus.exceptions import EquipmentError, TestError
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

    """
    BIST test commands for an example band (slot1)
    TX:ATTN 89.75       Set maximum attenuation
    TX:ENAB             Enable Tx
    TX:DUP DUP100       Set Slot 1
    TX:FORREV CLEAR     Clear forward/reverse
    TX:BW 5000000       Bandwidth 5MHz
    TX:TS:ENAB          Enable test signal
    TX:TS:FREQ 1000000  Set test signal frequency to 1MHz (offset)
    TX:FREQ 2654000000  Set Tx frequency to channel 
    TX:PAPATH PA_HIGH   Set the PA Path to HIGH (1 GHz - 3 GHz)
    TX:PAEN PA_HIGH     Enable the PA Path
    TX:ATTN 25          Set a sensible Atten
                        Now measure peak marker
    """

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
        slotNum: int = 0
        for hwId, bandName in self.product.getBands():
            logging.debug(f"Testing Slot: {slotNum}, Band:{bandName}")
            self.testBand(slotNum, hwId)
            slotNum += 1

        self.result = TxLevelTestResult(ResultStatus.PASSED)

    def finalise(self) -> bool:
        """End the test"""
        self.finaliseProduct()
        return super().finalise()

    def testBand(self, slotNum: int, hwId: int):
        """Test a selected Slot"""
        freqMHz = self.configProductForFreq(slotNum, hwId)
        self.specAna.setCentre(freqMHz + self.freqOffset)
        self.bist.set_attn(25)

        time.sleep(0.5)

        measuredPwr = self.specAna.getMaxMarker()
        detectedPwr = self.bist.get_pa_power(freqMHz)
        diff = detectedPwr - measuredPwr
        print(f"Frequency: {freqMHz} MHz, Measured: {measuredPwr}, detected: {detectedPwr}, diff: {diff}")

        time.sleep(1)
        self.bist.set_attn(BaseTactical.MAX_ATTENUATION)

    def configProductForFreq(self, slotNum: int, hwId: int) -> int:
        """Configures the product for a particular band"""
        self.filt = nesie_rx_filter_bands.RX_FILTER_BANDS_BY_ID[hwId]
        filt_dict = asdict(self.filt)
        logging.debug("RxFilterBand: hw_id=%s band=%s", self.filt.hardware_id, self.filt.band.name)
        for k, v in filt_dict.items():
            logging.debug("  %s = %r", k, v)

        setForwardReverse: bool = self.filt.extra_data & nesie_rx_filter_bands.EXTRA_DATA_SWAP_FOR_AND_REV_MASK == nesie_rx_filter_bands.EXTRA_DATA_SWAP_FOR_AND_REV_MASK

        if self.filt.direction_mask == nesie_rx_filter_bands.BOTH_DIR_MASK:
            # Tx Test want to use the downlink (towards cellular module from eNodeB)
            freq = int(self.filt.downlink.low_mhz + (self.filt.downlink.high_mhz - self.filt.downlink.low_mhz) / 2.0)
        elif self.filt.direction_mask == nesie_rx_filter_bands.UPLINK_DIR_MASK:
            # TDD channels will only have uplink listed
            freq = int(self.filt.uplink.low_mhz + (self.filt.uplink.high_mhz - self.filt.uplink.low_mhz) / 2.0)

            # I'm not sure if this is valid - that all TDD needs to SET the Fwd/Rev
            setForwardReverse = True
        else:
            raise TestError("Invalid filter band direction setting")

        # set the forward/reverse
        if setForwardReverse:
            self.bist.set_tx_fwd_rev("SET")
        else:
            self.bist.set_tx_fwd_rev("CLEAR")

        self.bist.set_duplexer(slotNum, "TX")
        self.bist.set_tx_freq(freq)
        self.bist.set_pa_on(freq)

        return freq

    def initProduct(self):
        self.product = self.getProduct()
        self.product.readFittedBands()

        self.product.openBIST()
        self.bist = cast(TacticalBISTCmds, self.product)

        # TX settings
        self.bist.set_attn(BaseTactical.MAX_ATTENUATION)    # TX:ATTN 89.75
        self.bist.set_tx_enable()                           # TX:ENAB
        self.bist.set_tx_bw(5)                              # TX:BW 5000000

        # TX:TS settings
        self.bist.set_ts_enable()                           # TX:TS:ENAB
        self.bist.set_ts_freq(self.freqOffset)              # TX:TS:FREQ 1000000

        dwell(0.5)

    def finaliseProduct(self):
        self.bist.set_attn(BaseTactical.MAX_ATTENUATION)
        self.bist.set_pa_off()
        self.bist.set_tx_disable()

    def configSpecAna(self):
        self.specAna = self.getEquip(BaseSpecAnalyser)
        cast(VISADevice, self.specAna).reset()

        self.specAna.setRefInput("INT")
        self.specAna.setSpan(10)
        self.specAna.setBWS("NUTT")
        self.specAna.setRBW(10)
        self.specAna.setVBW(10)
        self.specAna.setRefLevel(-10)
