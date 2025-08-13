import logging
import time
from typing import cast

from Cerberus.common import dwell
from Cerberus.exceptions import EquipmentError, ExecutionError
from Cerberus.plugins.baseParameters import (BaseParameters, NumericParameter,
                                             OptionParameter)
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.chambers.baseChamber import BaseChamber
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
    BaseSpecAnalyser
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.products.bist import TacticalBIST
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

    def run(self):
        super().run()

        self.configSpecAna()
        self.initProduct()

        self.result = TxLevelTestResult(ResultStatus.PASSED)

    def initProduct(self):
        # product will be a particular BIST class

        prod = cast(TacticalBIST, self.product)
        prod.set_attn(BaseTactical.MAX_ATTENUATION)
        prod.set_tx_enable()
        prod.set_duplexer(band, "TX")
        prod.set_forwardReverse("FWD")
        prod.set_tx_bw(5)
        prod.set_ts_enable()
        prod.set_ts_freq(TxLevelTest.AD9361_DC_NOTCH_FREQ_OFFSET)

        dwell(0.5)

    def configSpecAna(self):
        self.specAna = self.getEquip(BaseSpecAnalyser)
        if self.specAna is None:
            raise EquipmentError("Spectrum analyser is not found in equipement list")

        cast(VISADevice, self.specAna).reset()
        self.specAna.setRefInput("EXT")
        self.specAna.setSpan(1)
        self.specAna.setBWS("NUTT")
        self.specAna.setRBW(10)
        self.specAna.setVBW(10)
        self.specAna.setRefLevel(20)
