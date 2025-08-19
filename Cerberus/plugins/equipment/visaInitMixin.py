from typing import Any, cast

from Cerberus.exceptions import EquipmentError
from Cerberus.logConfig import getLogger
from Cerberus.plugins.equipment.baseEquipment import (BaseCommsEquipment,
                                                      Identity)
from Cerberus.plugins.equipment.visaDevice import VISADevice

logger = getLogger("VISA")


class VisaInitMixin:
    """Mixin providing common VISA initialisation/finalisation logic.

    Expects the consuming class to:
      - Inherit from VISADevice (so VISADevice methods are available)
      - Inherit from BaseEquipment (for getParameterValue/updateParameters & identity attribute)
      - Provide/update Communication parameter group (Port, IP Address, Timeout)
    """

    # Provided by BaseEquipment/BasePlugin in concrete subclass
    name: str

    def __init__(self):  # type: ignore[override]
        self._visa_opened = False

    # --- Internal helpers -----------------------------------------------------------------------------------------
    def _visa_initialise(self, init: Any | None = None) -> bool:
        commsEquip = cast(BaseCommsEquipment, self)
        comms = commsEquip.getGroupParameters("Communication")

        port = int(comms["Port"])
        ip = str(comms["IP Address"])
        timeout = int(comms["Timeout"])

        VISADevice.__init__(self, port=port, ipAddress=ip, timeout=timeout)  # type: ignore[misc]
        if VISADevice.open(self) is None:  # type: ignore[attr-defined]
            logger.error(f"Failed to open VISA resource {ip}:{port}")
            return False

        self._visa_opened = True
        idn = VISADevice.query(self, '*IDN?')  # type: ignore[attr-defined]
        if not idn:
            logger.error("Did not receive *IDN? response; closing VISA resource")
            self._visa_close_and_reset()
            return False

        # Parse identity and validate model matches plugin name
        self.identity = Identity(idn)
        if self.identity.model != self.name:
            self._visa_close_and_reset()
            logger.warning(f"Device identity {self.identity.model} is not the same as the equipment plugin {self.name}")
            return False

        return True

    def _visa_finalise(self) -> None:
        if self._visa_opened:
            try:
                VISADevice.close(self)  # type: ignore[attr-defined]
            finally:
                self._visa_opened = False

    # --- Internal utility ---------------------------------------------------------------------------------------
    def _visa_close_and_reset(self) -> None:
        """Close VISA resource (if open) and reset internal flag (idempotent)."""
        if self._visa_opened:
            try:
                VISADevice.close(self)  # type: ignore[attr-defined]
            except Exception:
                logger.debug("VISA close raised during cleanup", exc_info=True)

        self._visa_opened = False
