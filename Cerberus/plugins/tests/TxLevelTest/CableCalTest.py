from typing import cast

import numpy as np
from numpy.polynomial import Chebyshev

from Cerberus.common import dwell
from Cerberus.plugins.baseParameters import BaseParameters, NumericParameter
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.common import getSettledReading
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
    BaseSpecAnalyser
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import BaseTestResult


@hookimpl
@singleton
def createTestPlugin():
    return CableCalTest()


class TxLevelTestResult(BaseTestResult):
    def __init__(self, status):
        super().__init__("TxLevelTest", status)


class CableCalTestParams(BaseParameters):
    def __init__(self, ):
        super().__init__("Calibration")

        self.addParameter(NumericParameter("Start", 100, units="MHz", minValue=100, maxValue=3500, description="Start Frequency"))
        self.addParameter(NumericParameter("Stop", 3500, units="MHz", minValue=100, maxValue=3500, description="Stop Frequency"))
        self.addParameter(NumericParameter("Step", 100, units="MHz", minValue=10, maxValue=500, description="Step Frequency"))
        self.addParameter(NumericParameter("Power", 0, units="dBm", minValue=-40, maxValue=20, description="Signal Generator Output Power"))


class CableCalTest(BaseTest):
    def __init__(self):
        super().__init__("Cable Calibration")
        self._addRequirements([BaseSpecAnalyser, BaseSigGen])
        self.addParameterGroup(CableCalTestParams())

        self.specAna: BaseSpecAnalyser
        self.sigGen: BaseSigGen

    def run(self):
        super().run()

        calData: dict[int, float] = {}

        self.specAna = self.configSpecAna()
        self.sigGen = self.configSigGen()

        start = self.getParameterValue("Calibration", "Start", 100)
        stop = self.getParameterValue("Calibration", "Stop", 3500)
        step = self.getParameterValue("Calibration", "Step", 100)
        pwr = self.getParameterValue("Calibration", "Power", 0)

        self.sigGen.setOutputPower(pwr)
        self.sigGen.enablePower(True)

        for freq in range(start, stop + step, step):
            self.sigGen.setFrequency(freq)
            self.specAna.setCentre(freq)
            dwell(0.5)
            meas = getSettledReading(self.specAna.getMaxMarker)
            print(f"Freq: {freq} MHz, Power: {meas} dBm")
            calData[freq] = meas

        # Chebyshev fit (more numerically stable than plain polynomial)
        freqs = sorted(calData.keys())
        powers = [calData[f] for f in freqs]
        DEGREE = 20  # adjust if you need tighter error; must have len(freqs) > DEGREE
        if len(freqs) <= DEGREE:
            raise ValueError(f"Need more than {DEGREE} calibration points for Chebyshev degree {DEGREE}")
        cheb = Chebyshev.fit(freqs, powers, DEGREE, domain=[min(freqs), max(freqs)])
        print(f"Chebyshev degree {DEGREE} coefficients (ascending order for T_n):")
        print([float(c) for c in cheb.coef])

        # Go back through the step points and output difference between
        # measured and calibration Poly
        for freq in range(start, stop + step, step):
            offset = float(cheb(freq))
            diff = calData[freq] - offset
            print(f"{freq} MHz => Cal diff: {diff:+.3f} dB (meas {calData[freq]:.3f} vs fit {offset:.3f})")

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
        return specAna
        return specAna
