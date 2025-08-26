
import logging
from typing import Any

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.baseEquipment import BaseCommsEquipment
from Cerberus.plugins.equipment.powerMeters.basePowerMeters import \
    BasePowerMeter
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.equipment.visaInitMixin import VisaInitMixin


@hookimpl
@singleton
def createEquipmentPlugin():
    return N1913A()


class N1913A(BasePowerMeter, VISADevice, VisaInitMixin):
    def __init__(self):
        BasePowerMeter.__init__(self, "N1913A")
        VisaInitMixin.__init__(self)

    def initialise(self, init: Any | None = None) -> bool:
        if not self._visa_initialise(init):
            return False

        return BaseCommsEquipment.initialise(self)

    def setFrequency(self, freq: float) -> bool:
        """Sets the frequency (MHz)"""
        return self.command(f"FREQ {freq}MHZ")

    def getPowerReading(self) -> float:
        return float(self.query("FETCH?"))
