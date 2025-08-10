import logging
from typing import Any, Dict

from Cerberus.plugins.baseParameters import (BaseParameters, NumericParameter,
                                             StringParameter)
from Cerberus.plugins.basePlugin import BasePlugin


class Identity():
    def __init__(self, idString: str):
        parts = idString.split(",")
        if len(parts) == 4:
            self.manufacturer = parts[0]
            self.model = parts[1]
            self.serial = parts[2]
            self.version = parts[3]
        else:
            self.manufacturer = "Unknown"
            self.model = "Unknown"
            self.serial = "Unknown"
            self.version = "Unknown"

    def __str__(self) -> str:
        return f"{self.manufacturer} {self.model} [SN#{self.serial}, Version: {self.version.strip()}]"

    def __repr__(self) -> str:
        return str(self)


class CommsParams(BaseParameters):
    def __init__(self, ):
        super().__init__("Communication")

        self.addParameter(StringParameter("IP Address", "127.0.0.1", description="IP Address of the device"))
        self.addParameter(NumericParameter("Port", 5025, units="", minValue=0, maxValue=50000, description="Socket port number"))
        self.addParameter(NumericParameter("Timeout", 1000, units="ms", minValue=0, maxValue=10000, description="Communication timeout in milliseconds"))


class BaseEquipment(BasePlugin):
    def __init__(self, name):
        super().__init__(name)
        self.identity = Identity("")

        self.addParameterGroup(CommsParams())

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

    # --- Lifecycle -------------------------------------------------------------------------------------------------
    def initialise(self, init: Any | None = None) -> bool:
        logging.debug("Initialise")
        if isinstance(init, dict):
            self.updateParameters("Communication", init)

        self.initialised = True
        return True

    def configure(self, config: Any | None = None) -> bool:
        logging.debug("Configure")
        # Ensure we always store a dict
        if isinstance(config, dict):
            self.config.update(config)
        self.configured = True
        return True

    def finalise(self) -> bool:
        logging.debug("Finalise")
        self.initialised = False
        self.configured = False
        self.finalised = True
        return True
