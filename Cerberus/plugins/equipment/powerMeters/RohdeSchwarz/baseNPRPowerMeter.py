
import logging
from typing import Any

from Cerberus.plugins.equipment.baseEquipment import BaseCommsEquipment
from Cerberus.plugins.equipment.powerMeters.basePowerMeters import \
    BasePowerMeter
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.equipment.visaInitMixin import VisaInitMixin


class BaseNRPPowerMeter(BasePowerMeter, VISADevice, VisaInitMixin):
    def __init__(self, name):
        BasePowerMeter.__init__(self, name)
        VisaInitMixin.__init__(self)

    def initialise(self, init: Any | None = None) -> bool:
        if not self._visa_initialise(init):
            return False

        return BaseCommsEquipment.initialise(self)
