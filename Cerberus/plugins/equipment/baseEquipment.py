import logging
from typing import Any, Dict

from Cerberus.plugins.baseParameters import (BaseParameters, NumericParameter,
                                             StringParameter)
from Cerberus.plugins.basePlugin import BasePlugin
from Cerberus.plugins.commsParams import CommsParams


class Identity():
    def __init__(self, idString: str):
        parts = idString.split(",")
        if len(parts) == 4:
            self.manufacturer = parts[0].strip()
            self.model = parts[1].strip()
            self.serial = parts[2].strip()
            self.version = parts[3].strip()
        else:
            self.manufacturer = "Unknown"
            self.model = "Unknown"
            self.serial = "Unknown"
            self.version = "Unknown"

    def __str__(self) -> str:
        return f"{self.manufacturer} {self.model} [SN#{self.serial}, Version: {self.version.strip()}]"

    def __repr__(self) -> str:
        return str(self)


class BaseEquipment(BasePlugin):
    def __init__(self, name: str):
        super().__init__(name)
        self.identity = Identity("")
        self.addParameterGroup(CommsParams())

    def initComms(self, comms: Dict[str, Any]) -> None:
        """Initialise communication parameters from a dict (keys: 'IP Address','Port','Timeout')."""
        if isinstance(comms, dict):
            self.updateParameters("Communication", comms)

    def initialise(self, init: Any | None = None) -> bool:
        """Initialises the communication information"""
        return True

    def configure(self, config: Any | None = None) -> bool:
        logging.debug("Configure")
        return True

    def finalise(self) -> bool:
        logging.debug("Finalise")
        self._initialised = False
        self.configured = False
        self.finalised = True
        return True

    # --- Parameter Helpers -----------------------------------------------------------------------------------------
    def getParameterValue(self, group: str, paramName: str) -> Any | None:
        groupObj = self._groupParams.get(group)
        if not groupObj:
            return None
        param = groupObj.get(paramName)
        if not param:
            return None
        return param.value

    def setParameterValue(self, group: str, paramName: str, value: Any) -> bool:
        groupObj = self._groupParams.get(group)
        if not groupObj:
            return False
        param = groupObj.get(paramName)
        if not param:
            return False
        param.value = value
        return True

    def updateParameters(self, group: str, values: Dict[str, Any]):
        for k, v in values.items():
            self.setParameterValue(group, k, v)
