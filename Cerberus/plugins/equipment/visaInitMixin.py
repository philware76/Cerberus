import logging
from typing import Any

from Cerberus.plugins.equipment.baseCommsEquipment import Identity
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
        # Fetch parameters (fallback defaults)
        port = int(getattr(self, 'getParameterValue')("Communication", "Port") or 0)  # type: ignore[attr-defined]
        ip = str(getattr(self, 'getParameterValue')("Communication", "IP Address") or "127.0.0.1")  # type: ignore[attr-defined]
        timeout = int(getattr(self, 'getParameterValue')("Communication", "Timeout") or 1000)  # type: ignore[attr-defined]

        # (Re)initialise VISADevice portion explicitly
        VISADevice.__init__(self, port=port, ipAddress=ip, timeout=timeout)  # type: ignore[misc]
        if VISADevice.open(self) is None:  # type: ignore[attr-defined]
            logging.error(f"Failed to open VISA resource {ip}:{port}")
            return False

        self._visa_opened = True

        # Identify instrument
        idn = VISADevice.query(self, '*IDN?')  # type: ignore[attr-defined]
        if idn:
            # Identity attribute provided by BaseEquipment
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
