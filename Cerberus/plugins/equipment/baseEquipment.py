import logging
from typing import Any

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

        """
        Exclude this equipement from any dependency selection.
        Norminally this is set to False, but can be used to quickly 
        exlcude equipment while developing the test system.
        """
        self.excluded = False

    def initialise(self, init: Any | None = None) -> bool:
        """Initialises the equipment"""
        logging.debug("Initialise")
        return True

    def finalise(self) -> bool:
        """Finalises [closes] the equipment"""
        logging.debug("Finalise")
        self.finalised = True
        return True


class BaseCommsEquipment(BaseEquipment):
    def __init__(self, name: str):
        super().__init__(name)
        self.identity = Identity("")
        self.addParameterGroup(CommsParams())

    def initComms(self, comms: dict[str, Any]) -> None:
        """Initialise communication parameters from a dict (keys: 'IP Address','Port','Timeout')."""
        if isinstance(comms, dict):
            self.updateParameters("Communication", comms)
