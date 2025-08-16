import logging
from typing import Any, cast

from Cerberus.plugins.equipment.baseEquipment import (BaseCommsEquipment,
                                                      Identity)
from Cerberus.plugins.equipment.visaDevice import VISADevice


class VisaInitMixin:
    """Mixin providing common VISA initialisation/finalisation logic.

    Expects the consuming class to:
      - Inherit from VISADevice (so VISADevice methods are available)
      - Inherit from BaseEquipment (for getParameterValue/updateParameters & identity attribute)
      - Provide/update Communication parameter group (Port, IP Address, Timeout)
    """

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
            logging.error(f"Failed to open VISA resource {ip}:{port}")
            return False

        self._visa_opened = True

        idn = VISADevice.query(self, '*IDN?')  # type: ignore[attr-defined]
        if idn:
            self.identity = Identity(idn)  # type: ignore[attr-defined]
            return True

        logging.error("Did not receive *IDN? response; closing VISA resource")
        VISADevice.close(self)  # type: ignore[attr-defined]
        self._visa_opened = False

        return False

    def _visa_finalise(self) -> None:
        if self._visa_opened:
            try:
                VISADevice.close(self)  # type: ignore[attr-defined]
            finally:
                self._visa_opened = False
                self._visa_opened = False
