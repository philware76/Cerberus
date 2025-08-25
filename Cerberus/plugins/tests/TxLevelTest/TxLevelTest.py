import json
import logging
import time
from dataclasses import asdict
from typing import Any, cast

from numpy.polynomial import Chebyshev

from Cerberus.common import dwell
from Cerberus.exceptions import EquipmentError, TestError
from Cerberus.plugins.baseParameters import (BaseParameters, NumericParameter,
                                             OptionParameter, StringParameter)
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.cables.RXCalCableEquipment import RXCalCable
from Cerberus.plugins.equipment.cables.TXCalCableEquipment import TXCalCable
from Cerberus.plugins.equipment.powerMeters.basePowerMeters import \
    BasePowerMeter
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


class TestSpecParams(BaseParameters):
    def __init__(self, ):
        super().__init__("Test Specs")

        self.addParameter(NumericParameter("Detected-Measured", 3.0, units="dB", minValue=0, maxValue=20,
                                           description="The maximum difference between the detected power and measured power can be."))


class RfTestParams(BaseParameters):
    def __init__(self, ):
        super().__init__("RF Parameters")

        self.addParameter(NumericParameter("Tx Attn", 25, units="dB", minValue=0, maxValue=50, description="The TX Attenuation setting of NESIE"))
        self.addParameter(NumericParameter("Cable Attn", 10.0, units="dB", minValue=0, maxValue=50, description="The attenuator on the cable"))
        self.addParameter(StringParameter(
            "Coeffs",
            value='{"coeffs": [-1.609141417150715, -0.6757908354285234, 0.058674614875468135, '
            '-0.0031915753722614125, -0.021765415467106336, 0.016691035032112896, '
            '-0.013077298931293337, 0.004910903969558918, -0.008379936478786022], '
            '"domain": [600.0, 3500.0], "window": [-1.0, 1.0]}',
            description="Chebyshev coefficents"))

        self.addParameter(OptionParameter("Enable cable calibration", value=True, description="If cable calibration is enabled, Coeffs will be used"))


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
        self._addRequirements([BasePowerMeter, TXCalCable, RXCalCable])
        self.addParameterGroup(RfTestParams())
        self.addParameterGroup(TestSpecParams())

        self.bist: TacticalBISTCmds | None = None
        self.freqOffset: int = TxLevelTest.AD9361_DC_NOTCH_FREQ_OFFSET
        self.pwrCalAdjust: Chebyshev
        self.filt = None  # set in configProductForFreq

        self.rfParams = self.getGroupParameters("RF Parameters")
        self.testSpec = self.getGroupParameters("Test Specs")

    def run(self) -> None:
        super().run()
        if self.product is None:
            raise EquipmentError(f"{self.name} test requires a product type to be set before test")

        self.TxAttn = float(self.rfParams["Tx Attn"])
        self.cableAttn = float(self.rfParams["Cable Attn"])

        self.usePwrcalAdjust = bool(self.rfParams["Enable cable calibration"])

        if self.usePwrcalAdjust:
            try:
                coeffs_raw = str(self.rfParams["Coeffs"])
                self.coeffs = json.loads(coeffs_raw)
                self.pwrCalAdjust = Chebyshev(self.coeffs['coeffs'], domain=self.coeffs['domain'], window=self.coeffs['window'])

            except json.JSONDecodeError:
                raise ValueError("Failed to decode the Cable Cal Coeffs json string in the test parameters")

        else:
            # A null filter - will always return 0 as the calibration value
            self.pwrCalAdjust = Chebyshev([0, 0], domain=[600, 3500], window=[-1.0, 1.0])

        self.configurePowerMeter()
        self.initProduct()

        slotNum = 0
        for hwId, bandName in self.product.getBands():
            if hwId != 0xFF:
                logging.debug(f"Testing Slot: {slotNum}, Band:{bandName}")
                result = self.testBand(slotNum, hwId)
                print(result)
            else:
                logging.debug(f"Skipping slot: {slotNum} - Empty")

            slotNum += 1

    def finalise(self):
        self.finaliseProduct()
        return super().finalise()

    def testBand(self, slotNum: int, hwId: int) -> dict[str, Any]:
        assert self.powerMeter is not None and self.bist is not None

        freqMHz, path = self.configProductForFreq(slotNum, hwId)
        self.powerMeter.setFrequency(freqMHz + self.freqOffset)
        self.bist.set_attn(self.TxAttn)
        time.sleep(0.5)

        pwrCalAdjustment = float(self.pwrCalAdjust(freqMHz + self.freqOffset))
        rawPwr = self.take_power_measurement(freqMHz + self.freqOffset)

        measuredPwr = round(rawPwr - pwrCalAdjustment + self.cableAttn, 2)
        detectedPwr = self.bist.get_pa_power(freqMHz)
        diff = detectedPwr - measuredPwr
        band_name = getattr(getattr(self.filt, 'band', None), 'name', 'Unknown')

        # check if the difference between detected and measured is within the spec
        passed = abs(diff) < float(self.testSpec["Detected-Measured"])
        if not passed:
            self.result.status = ResultStatus.FAILED

        # Create measurement result dictionary
        result = {
            "slot": slotNum,
            "band": band_name,
            "path": path,
            "frequency_mhz": freqMHz,
            "measured_power": round(measuredPwr, 2),
            "calibration_adjustment": round(pwrCalAdjustment, 2),
            "detected_power": round(detectedPwr, 2),
            "difference": round(diff, 2),
            "passed": passed
        }

        self.result.addTestResult("BandResults", result)

        return result

    def configProductForFreq(self, slotNum: int, hwId: int) -> tuple[int, str]:
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
        path = self.bist.set_duplexer(slotNum, "TX")
        self.bist.set_tx_freq(freq)
        self.bist.set_pa_on(freq)

        return freq, path

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
