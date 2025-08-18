import time
from typing import cast

from numpy.polynomial import Chebyshev

from Cerberus.common import dwell
from Cerberus.gui.helpers import openMatPlotUI
from Cerberus.plugins.baseParameters import BaseParameters, NumericParameter
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.common import getSettledReading
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
    BaseSpecAnalyser
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import BaseTestResult, ResultStatus


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

        self.addParameter(NumericParameter("MinSamples", 10, minValue=5, maxValue=100, description="Minimum number of readings per measurement"))
        self.addParameter(NumericParameter("Chebyshev Degree", 8, minValue=5, maxValue=30, description="Chebyshev degree of coeffs"))


class CableCalTest(BaseTest):
    def __init__(self):
        super().__init__("Cable Calibration", checkProduct=False)
        self._addRequirements([BaseSpecAnalyser, BaseSigGen])
        self.addParameterGroup(CableCalTestParams())

        self.specAna: BaseSpecAnalyser
        self.sigGen: BaseSigGen

    def run(self):
        super().run()

        calData: dict[int, float] = {}

        self.specAna = self.configSpecAna()
        self.sigGen = self.configSigGen()

        self.gp = self.getGroupParameters("Calibration")
        start = int(self.gp["Start"])
        stop = int(self.gp["Stop"])
        step = int(self.gp["Step"])
        pwr = int(self.gp["Power"])

        self.sigGen.setOutputPower(pwr)
        self.sigGen.setPowerState(True)

        freqRange = range(start, stop + step, step)

        # Axis ranges per requirement: X from (start - step) to (stop + step); Y from -43 to -39 dBm
        xlim = (start - step, stop + step)
        ylim = (-43, -39)

        app, window, matplot = openMatPlotUI(
            "Cable Calibration",
            "Frequency (MHz)",
            "Offset (dB)",
            xlim=xlim,
            ylim=ylim,
            series=["Cal"],
            window_title="Cable Calibration Live"
        )

        for freq in freqRange:
            markerPwr = self.takeMarkerMeas(freq)
            calData[freq] = markerPwr
            matplot.append_point("Cal", freq, markerPwr)
            app.processEvents()

        cheb = self.calcCalCoeffs(calData)
        self.checkCalCoeffs(freqRange, calData, cheb)

        self.result = CableCalTestResult(ResultStatus.PASSED)
        self.result.log = self.getLog()

        try:
            while window.isVisible():
                app.processEvents()
                time.sleep(0.05)

        except Exception:
            pass

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

    def takeMarkerMeas(self, freq):
        self.sigGen.setFrequency(freq)
        self.specAna.setCentre(freq)
        dwell(0.5)

        self.specAna.setMarkerPeak()
        dwell(0.5)

        minSamples = minSamples = int(self.gp["MinSamples"])
        markerPwr = getSettledReading(self.specAna.getMarkerPower, minSamples)
        markerPwr = round(markerPwr, 2)

        markerFreq = self.specAna.getMarkerFreq()
        markerFreq = round(markerFreq/1e6, 2)

        self.logger.info(f"Freq: {freq} MHz, MarkerFreq: {markerFreq} MHz, MarkerPower: {markerPwr} dBm")

        return markerPwr

    def configSigGen(self) -> BaseSigGen:
        sigGen = self.getEquip(BaseSigGen)
        cast(VISADevice, sigGen).reset()

        return sigGen

    def configSpecAna(self) -> BaseSpecAnalyser:
        specAna = self.getEquip(BaseSpecAnalyser)
        cast(VISADevice, specAna).reset()

        specAna.setRefInput("INT")
        specAna.setSpan(10)
        specAna.setBWS("NUTT")
        specAna.setRBW(10)
        specAna.setVBW(10)
        specAna.setRefLevel(-10)

        return specAna
