import time
from typing import cast

from numpy.polynomial import Chebyshev

from Cerberus.gui.helpers import getGlobalMatPlotUI
from Cerberus.logConfig import getLogger
from Cerberus.plugins.baseParameters import BaseParameters, NumericParameter
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.powerMeters.basePowerMeters import \
    BasePowerMeter
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import BaseTestResult, ResultStatus
from Cerberus.plugins.tests.mixins.powerMeasurementMixin import \
    PowerMeasurementMixin

logger = getLogger("CableCalTest")


@hookimpl
@singleton
def createTestPlugin():
    return CableCalTest()


class CableCalTestResult(BaseTestResult):
    def __init__(self, status: ResultStatus):
        super().__init__("TxLevelTest", status)


class CableCalTestParams(BaseParameters):
    def __init__(self, ):
        super().__init__("Calibration")

        self.addParameter(NumericParameter("Start", 100, units="MHz", minValue=100, maxValue=3500, description="Start Frequency"))
        self.addParameter(NumericParameter("Stop", 3500, units="MHz", minValue=100, maxValue=3500, description="Stop Frequency"))
        self.addParameter(NumericParameter("Step", 100, units="MHz", minValue=10, maxValue=500, description="Step Frequency"))
        self.addParameter(NumericParameter("Power", 0, units="dBm", minValue=-40, maxValue=20, description="Signal Generator Output Power"))
        self.addParameter(NumericParameter("Atten", 40, units="dBm", minValue=00, maxValue=40, description="Attenuator(s) on the cable"))

        self.addParameter(NumericParameter("MinSamples", 10, minValue=5, maxValue=100, description="Minimum number of readings per measurement"))
        self.addParameter(NumericParameter("Chebyshev Degree", 8, minValue=5, maxValue=30, description="Chebyshev degree of coeffs"))


class CableCalTest(PowerMeasurementMixin, BaseTest):
    powerMeter: BasePowerMeter
    sigGen: BaseSigGen

    def __init__(self):
        super().__init__("Cable Calibration", checkProduct=False)
        self._addRequirements([BasePowerMeter, BaseSigGen])
        self.addParameterGroup(CableCalTestParams())
        # Attributes set during configuration
        self.powerMeter = cast(BasePowerMeter, None)
        self.sigGen = cast(BaseSigGen, None)

    def run(self):
        super().run()

        calData: dict[int, float] = {}
        self.configEquipment()

        self.gp = self.getGroupParameters("Calibration")
        logger.info(self.gp)

        start = int(self.gp["Start"])
        stop = int(self.gp["Stop"])
        step = int(self.gp["Step"])
        pwr = int(self.gp["Power"])
        atten = int(self.gp["Atten"])

        self.sigGen.setOutputPower(pwr)
        self.sigGen.setPowerState(True)

        freqRange = range(start, stop + step, step)
        xlim = (start - step, stop + step)
        ylim = (-5, 5)

        # Obtain (or create) persistent global plot UI.
        gpui = getGlobalMatPlotUI(
            title="Cable Calibration",
            xlabel="Frequency (MHz)",
            ylabel="Offset (dB)",
            xlim=xlim,
            ylim=ylim,
            window_title="Cable Calibration Live"
        )
        series_name = gpui.new_series("CalRun")

        for freq in freqRange:
            self.sigGen.setFrequency(freq)
            meas = self.take_power_measurement(freq) + atten
            logger.debug(f"Set frequency: {freq}, Power: {meas:.2f} dBm")

            calData[freq] = meas
            gpui.append_point(series_name, freq, meas)

        polyFit = self.calcCalCoeffs(calData)
        self.checkCalCoeffs(freqRange, calData, polyFit)

        self.result = CableCalTestResult(ResultStatus.PASSED)
        self.result.log = self.getLog()

    def configEquipment(self):
        self.sigGen = self.configSigGen()
        # Unified setup via mixin
        self.setup_power_path()

    def checkCalCoeffs(self, freqRange, calData, cheb):
        for freq in freqRange:
            offset = float(cheb(freq))
            diff = calData[freq] - offset
            print(f"{freq} MHz => Cal diff: {diff:+.3f} dB Meas: {calData[freq]:.3f} vs Fit: {offset:.3f}")

    def calcCalCoeffs(self, calData):
        # Chebyshev fit (more numerically stable than plain polynomial)
        freqs = sorted(calData.keys())
        powers = [calData[f] for f in freqs]
        degree = int(self.gp["Chebyshev Degree"])

        cheb = Chebyshev.fit(freqs, powers, degree, domain=[min(freqs), max(freqs)])
        print(f"Chebyshev degree {degree} coefficients (ascending order for T_n):")
        print([float(c) for c in cheb.coef])

        return cheb

    def configSigGen(self) -> BaseSigGen:
        sigGen = self.getEquip(BaseSigGen)
        cast(VISADevice, sigGen).reset()

        return sigGen
