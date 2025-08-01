import logging
from typing import Any

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.baseEquipment import Identity
from Cerberus.plugins.equipment.signalGenerators.baseSigGen import BaseSigGen
from Cerberus.plugins.equipment.visaDevice import VISADevice


@hookimpl
@singleton
def createEquipmentPlugin():
    return VSG60CEquipment()

class VSG60CEquipment(BaseSigGen):
    def __init__(self):
        super().__init__("VSG60C Signal Generator")
        self.identity: Identity | None
        self.visa: VISADevice

        self._init = {"Port": 5025, "IPAddress": "127.0.0.1"}

    def initialise(self, init: Any | None = None) -> bool:
        if self.initialised:
            return True

        if init is not None:
            super().initialise(init)

        self.visa = VISADevice(self._init["Port"], self._init["IPAddress"])
        if self.visa.open() is None:
            logging.error("Failed to open the VSG60C Signal Generator")
            return False

        self.identity = self.visa.identity()
        if self.identity is not None:
            self.initialised = True
            return True

        return False

    def finalise(self) -> bool:
        if self.visa.close():
            return super().finalise()
        else:
            return False