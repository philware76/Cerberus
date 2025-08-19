import logging
import time
from dataclasses import asdict
from typing import cast

from numpy.polynomial import Chebyshev

from Cerberus.common import dwell
from Cerberus.exceptions import EquipmentError, TestError
from Cerberus.plugins.baseParameters import BaseParameters, NumericParameter
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.cables.RXCalCableEquipment import RXCalCable
from Cerberus.plugins.equipment.cables.TXCalCableEquipment import TXCalCable
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
    BaseSpecAnalyser
from Cerberus.plugins.products.bist import TacticalBISTCmds
from Cerberus.plugins.products.nesieFirmware import nesie_rx_filter_bands
from Cerberus.plugins.products.tactical.tactical import BaseTactical
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import BaseTestResult, ResultStatus
from Cerberus.plugins.tests.mixins.powerMeasurementMixin import \
    PowerMeasurementMixin


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

        self.addParameter(NumericParameter("Tx Attn", 25, units="dB", minValue=0, maxValue=50, description="The TX Attenuation setting of NESIE"))
        self.addParameter(NumericParameter("Cable Cal", 40.0, units="dB", minValue=0, maxValue=50, description="The loss of the connecting SMA cable"))


class TxLevelTest(PowerMeasurementMixin, BaseTest):
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

    def __init__(self) -> None:
        super().__init__("Tx Level")
        self._addRequirements([BaseSpecAnalyser, BaseSigGen, TXCalCable, RXCalCable])
        self.addParameterGroup(TxLevelTestParameters())

        self.bist: TacticalBISTCmds | None = None
        self.freqOffset: int = TxLevelTest.AD9361_DC_NOTCH_FREQ_OFFSET
        self.specAna: BaseSpecAnalyser | None = None
        self.cheb: Chebyshev | None = None
        self.filt = None  # set in configProductForFreq

    def run(self) -> None:
        super().run()
        if self.product is None:
            raise EquipmentError(f"{self.name} test requires a product type to be set before test")

        gp = self.getGroupParameters("RF Parameters")
        self.TxAttn = float(gp["Tx Attn"])  # preserve naming convention
        self.cableCal = float(gp["Cable Cal"])  # preserve naming convention

        # Ensure we are using a spectrum analyser
        self.setup_power_path()
        self.specAna = cast(BaseSpecAnalyser, self.powerMeter)
        self.initProduct()
        self.cheb = self.getCheb()

        slotNum = 0
        for hwId, bandName in self.product.getBands():
            if hwId != 0xFF:
                logging.debug(f"Testing Slot: {slotNum}, Band:{bandName}")
                self.testBand(slotNum, hwId)
            else:
                logging.debug(f"Skipping slot: {slotNum} - Empty")
            slotNum += 1

        self.result = TxLevelTestResult(ResultStatus.PASSED)

    def finalise(self) -> bool:
        self.finaliseProduct()
        return super().finalise()

    def getCheb(self) -> Chebyshev:
        coeffs = [-41.050163553316416, -1.223352951884796, -0.046113614071520224, -0.04349724582375006, 0.1687123666141453, 0.05756109857165281, -0.026992299889912127, -0.05707854541034618, 0.0016636832612212716, -0.0032157438867030305,
                  0.01920038523659272, 0.03717463796923275, 0.07374152755709508, 0.09264865048317557, 0.02034832268232638, -0.01478322226821526, -0.060596621395038915, -0.011138690543777637, 0.0077710190338166635, 0.023636552233819313, -0.011987505135510714]
        return Chebyshev(coeffs, domain=[100, 3500])

    def testBand(self, slotNum: int, hwId: int) -> None:
        assert self.specAna is not None and self.bist is not None and self.cheb is not None
        freqMHz = self.configProductForFreq(slotNum, hwId)
        self.specAna.setCentre(freqMHz + self.freqOffset)
        self.bist.set_attn(25)
        time.sleep(0.5)
        calOffset = self.cheb(freqMHz + self.freqOffset)
        rawPwr = self.take_power_measurement(freqMHz + self.freqOffset)
        measuredPwr = rawPwr - calOffset
        detectedPwr = self.bist.get_pa_power(freqMHz)
        diff = detectedPwr - measuredPwr
        band_name = getattr(getattr(self.filt, 'band', None), 'name', 'Unknown')
        print(
            f"Slot: {slotNum}, Band: {band_name}, Freq: {freqMHz} MHz, "
            f"Measured: {measuredPwr} (cal: {calOffset}), detected: {detectedPwr}, diff: {diff}"
        )
        time.sleep(1)
        self.bist.set_attn(BaseTactical.MAX_ATTENUATION)

    def configProductForFreq(self, slotNum: int, hwId: int) -> int:
        assert self.bist is not None
        self.filt = nesie_rx_filter_bands.RX_FILTER_BANDS_BY_ID[hwId]
        filt_dict = asdict(self.filt)
        logging.debug("RxFilterBand: hw_id=%s band=%s", self.filt.hardware_id, self.filt.band.name)
        for k, v in filt_dict.items():
            logging.debug("  %s = %r", k, v)

        setForwardReverse = self.filt.extra_data & nesie_rx_filter_bands.EXTRA_DATA_SWAP_FOR_AND_REV_MASK == nesie_rx_filter_bands.EXTRA_DATA_SWAP_FOR_AND_REV_MASK
        if self.filt.direction_mask == nesie_rx_filter_bands.BOTH_DIR_MASK:
            freq = int(self.filt.downlink.low_mhz + (self.filt.downlink.high_mhz - self.filt.downlink.low_mhz) / 2.0)
        elif self.filt.direction_mask == nesie_rx_filter_bands.UPLINK_DIR_MASK:
            freq = int(self.filt.uplink.low_mhz + (self.filt.uplink.high_mhz - self.filt.uplink.low_mhz) / 2.0)
            setForwardReverse = True
        else:
            raise TestError("Invalid filter band direction setting")

        self.bist.set_tx_fwd_rev("SET" if setForwardReverse else "CLEAR")
        self.bist.set_duplexer(slotNum, "TX")
        self.bist.set_tx_freq(freq)
        self.bist.set_pa_on(freq)
        return freq

    def initProduct(self) -> None:
        self.product = self.getProduct()
        self.product.readFittedBands()
        self.product.openBIST()
        self.bist = cast(TacticalBISTCmds, self.product)
        if self.bist is None:
            raise EquipmentError("BIST not available")

        self.bist.set_attn(BaseTactical.MAX_ATTENUATION)
        self.bist.set_tx_enable()
        self.bist.set_tx_bw(5)
        self.bist.set_ts_enable()
        self.bist.set_ts_freq(self.freqOffset)
        dwell(0.5)

    def finaliseProduct(self) -> None:
        if self.bist is None:
            return
        self.bist.set_attn(BaseTactical.MAX_ATTENUATION)
        self.bist.set_pa_off()
        self.bist.set_tx_disable()

    def setup_power_path(self) -> None:  # type: ignore[override]
        # Force spectrum analyser usage (test relies on marker measurements)
        self.powerMeter = self.getEquip(BaseSpecAnalyser)  # type: ignore[attr-defined]
        self._config_spec_analyser(cast(BaseSpecAnalyser, self.powerMeter))
