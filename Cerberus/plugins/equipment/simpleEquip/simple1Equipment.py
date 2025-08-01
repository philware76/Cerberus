import logging
from typing import Any

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment, Identity
from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
    BaseSpecAnalyser
from Cerberus.plugins.equipment.visaDevice import VISADevice


@hookimpl
@singleton
def createEquipmentPlugin():
    return SimpleEquip1()


class SimpleEquip1(BaseEquipment):
    def __init__(self):
        super().__init__("Simple Equipment #1")
        self.identity: Identity | None = None
        # self.visa: VISADevice

        self._init = {"Port": 5025, "IPAddress": "127.0.0.1"}
        