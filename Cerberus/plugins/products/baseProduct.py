import logging
from typing import Any, ClassVar

from Cerberus.plugins.basePlugin import BasePlugin
from Cerberus.plugins.products.bandNames import BandNames
from Cerberus.plugins.products.eeprom import EEPROM, FittedBands
from Cerberus.plugins.products.sshComms import SSHComms


class BaseProduct(BasePlugin):
    # Default class-level mappings; product implementations should override
    SLOT_DETAILS_DICT: ClassVar[dict[int, BandNames]] = {}
    FILTER_DICT: ClassVar[dict[int, BandNames]] = {}

    def __init__(self, name: str, description: str | None = None):
        super().__init__(name, description)

        # Cached raw EEPROM 32-bit word strings (hex)
        self._eeprom_words: list[str] = []

        # Cached fitted bands (resolved BandNames)
        self.fitted_bands: list[BandNames] = []

        # Remember last DA host used for refresh
        self.da_host: str | None = None

    def initialise(self, init: Any = None) -> bool:
        logging.debug("Initialise")
        return True

    def configure(self, config: Any = None) -> bool:
        logging.debug("Configure")
        return True

    def finalise(self) -> bool:
        logging.debug("Finalise")
        return True

    def refresh_fitted_bands(self, host: str) -> bool:
        """Reads the fitted bands from the eeprom"""

        self._da_host = host
        key_path = "Keys/id_rsa.zynq"

        try:
            with SSHComms(host, username="root", key_path=key_path) as ssh:
                eep = EEPROM(ssh)
                words = eep.read() or []

        except Exception as e:
            logging.warning("EEPROM read failed on %s: %s", host, e)
            return False

        if words == self._eeprom_words and self.fitted_bands:
            return True  # No change

        self._eeprom_words = words
        if not words:
            self.fitted_bands = []
            return False

        try:
            self.fitted_bands = FittedBands.bands(words, self.SLOT_DETAILS_DICT, self.FILTER_DICT) or []

        except Exception as e:
            logging.warning("Fitted bands parse failed: %s", e)
            self.fitted_bands = []
            return False

        return True
