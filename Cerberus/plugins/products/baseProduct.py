import logging
from pathlib import Path  # added
from typing import Any, ClassVar

from Cerberus.plugins.basePlugin import BasePlugin
from Cerberus.plugins.products.bandNames import BandNames
from Cerberus.plugins.products.bist import BaseBIST
from Cerberus.plugins.products.eeprom import EEPROM, FittedBands
from Cerberus.plugins.products.sshComms import SSHComms


class BaseProduct(BasePlugin, BaseBIST):
    # Default class-level mappings; product implementations should override
    SLOT_DETAILS_DICT: ClassVar[dict[int, BandNames]] = {}
    FILTER_DICT: ClassVar[dict[int, BandNames]] = {}

    def __init__(self, name: str, description: str | None = None):
        """Initialise BaseProduct and explicitly run BaseBIST.__init__"""
        super().__init__(name, description)          # BasePlugin.__init__
        BaseBIST.__init__(self)  # ensure _client attribute exists

        self._eepromWords = []
        self._fittedBands = []
        self._DAHost = None

    def setDAHost(self, host):
        self._DAHost = host
        self.initBIST(self._DAHost)

    def initialise(self, init: Any = None) -> bool:
        logging.debug("Initialise")
        return True

    def configure(self, config: Any = None) -> bool:
        logging.debug("Configure")
        return True

    def finalise(self) -> bool:
        logging.debug("Finalise")
        return True

    # --- Internal helpers -------------------------------------------------
    def _resolve_key_path(self) -> Path:
        """Return absolute path to private key (plugins/products/Keys/id_rsa.zynq)."""
        # baseProduct.py lives in plugins/products; just append Keys
        key_path = (Path(__file__).resolve().parent / "Keys" / "id_rsa.zynq").resolve()
        if not key_path.exists():
            logging.warning("Product SSH key not found at %s", key_path)

        return key_path

    def readFittedBands(self) -> bool:
        """Reads the fitted bands from the EEPROM on the given host and caches them."""
        key_path = self._resolve_key_path()

        if self._DAHost is None:
            raise ValueError("DA Host has not been set")

        try:
            with SSHComms(self._DAHost, username="root", key_path=key_path) as ssh:
                eep = EEPROM(ssh)
                words = eep.read() or []
        except Exception as e:
            logging.warning("EEPROM read failed on %s: %s", self._DAHost, e)
            return False

        self._eepromWords = words
        if not words:
            self._fittedBands = []
            return False

        try:
            self._fittedBands = FittedBands.bands(words, self.SLOT_DETAILS_DICT, self.FILTER_DICT) or []
        except Exception as e:
            logging.warning("Fitted bands parse failed: %s", e)
            self._fittedBands = []
            return False

        return True

    def getBands(self) -> list[tuple[int, BandNames]]:
        """Public accessor; returns cached list (may be empty if not yet refreshed)."""
        return list(self._fittedBands)
