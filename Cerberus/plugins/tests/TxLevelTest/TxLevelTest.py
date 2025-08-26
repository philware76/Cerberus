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

        # Create parameters
        fullBandSweepOption = OptionParameter("Full band sweep", False, description="Performs the Tx Level Test over the full band")
        stepValue = NumericParameter("MHz step", 100, units="MHz", minValue=10, maxValue=500, description="When performing a band sweep, use this value as the step")

        self.addParameter(fullBandSweepOption)
        self.addParameter(stepValue)
        stepValue.setWidgetDependency("enabled", fullBandSweepOption)


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
        self.filt = None

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
                results = self.testBand(slotNum, hwId)
                for result in results:
                    print(result)
            else:
                logging.debug(f"Skipping slot: {slotNum} - Empty")

            slotNum += 1

    def finalise(self):
        self.finaliseProduct()
        return super().finalise()

    def testBand(self, slotNum: int, hwId: int) -> list[dict[str, Any]]:
        """Test a band at multiple frequencies and return list of results."""
        assert self.powerMeter is not None and self.bist is not None

        # Configure the nesie's hardward for this slot / hardware band ID
        path = self.setProductForBandHwId(slotNum, hwId)

        # Get the frequency list to run the test over
        if bool(self.testSpec["Full band sweep"]):
            step = int(self.testSpec["MHz step"])
            freq_path_list = self.getBandFrequencyRange(step)
        else:
            freq_path_list = self.getBandCenterFrequency()

        results = []

        for freqMHz in freq_path_list:
            self.configEquipment(freqMHz)

            # Read the measurement from the power meter
            pwrCalAdjustment = float(self.pwrCalAdjust(freqMHz + self.freqOffset))
            rawPwr = self.take_power_measurement(freqMHz + self.freqOffset)
            measuredPwr = round(rawPwr - pwrCalAdjustment + self.cableAttn, 2)

            # Read the internal detected power
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

            # save the result
            self.result.addTestResult("BandResults", result)
            results.append(result)

        return results

    def configEquipment(self, freqMHz):
        assert self.powerMeter is not None and self.bist is not None

        # Configure frequency-specific settings
        self.bist.set_tx_freq(freqMHz)
        self.bist.set_pa_on(freqMHz)

        self.powerMeter.setFrequency(freqMHz + self.freqOffset)
        self.bist.set_attn(self.TxAttn)
        time.sleep(0.5)

    def setProductForBandHwId(self, slotNum, hwId):
        """Configure product for frequencies and return list of (frequency, path) tuples to test."""
        self.filt = nesie_rx_filter_bands.RX_FILTER_BANDS_BY_ID[hwId]
        filt_dict = asdict(self.filt)

        logging.debug("RxFilterBand: hw_id=%s band=%s", self.filt.hardware_id, self.filt.band.name)
        for k, v in filt_dict.items():
            logging.debug("  %s = %r", k, v)

        setForwardReverse = self.filt.extra_data & nesie_rx_filter_bands.EXTRA_DATA_SWAP_FOR_AND_REV_MASK == nesie_rx_filter_bands.EXTRA_DATA_SWAP_FOR_AND_REV_MASK or \
            self.filt.direction_mask == nesie_rx_filter_bands.UPLINK_DIR_MASK

        assert self.bist is not None
        self.bist.set_tx_fwd_rev("SET" if setForwardReverse else "CLEAR")
        path = self.bist.set_duplexer(slotNum, "TX")

        return path

    def getBandCenterFrequency(self) -> list[int]:
        # Determine which band to use based on direction mask
        if self.filt.direction_mask == nesie_rx_filter_bands.BOTH_DIR_MASK:
            band = self.filt.downlink
        elif self.filt.direction_mask == nesie_rx_filter_bands.UPLINK_DIR_MASK:
            band = self.filt.uplink
        else:
            raise TestError("Invalid filter band direction setting")

        # Calculate center frequency of the selected band and return in a list
        freq = int(band.low_mhz + (band.high_mhz - band.low_mhz) / 2.0)
        return [freq]

    def getBandFrequencyRange(self, step_mhz: int) -> list[int]:
        """
        Generate a list of frequencies from low_mhz to high_mhz at specified step intervals.

        Args:
            step_mhz: The frequency step size in MHz

        Returns:
            List of frequencies in MHz from low to high at step_mhz intervals, 
            always including the high frequency
        """
        # Determine which band to use based on direction mask
        if self.filt.direction_mask == nesie_rx_filter_bands.BOTH_DIR_MASK:
            band = self.filt.downlink
        elif self.filt.direction_mask == nesie_rx_filter_bands.UPLINK_DIR_MASK:
            band = self.filt.uplink
        else:
            raise TestError("Invalid filter band direction setting")

        # Generate frequencies for the selected band
        test_frequencies = []
        low_freq = int(band.low_mhz)
        high_freq = int(band.high_mhz)

        freq = low_freq
        while freq <= high_freq:
            test_frequencies.append(freq)
            freq += step_mhz

        # Ensure high frequency is included if not already present
        if test_frequencies[-1] != high_freq:
            test_frequencies.append(high_freq)

        return test_frequencies

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
