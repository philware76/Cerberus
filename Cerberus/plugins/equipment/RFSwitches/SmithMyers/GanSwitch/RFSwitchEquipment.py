import logging
import time
from typing import Any

import requests

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.baseCommsEquipment import (BaseCommsEquipment,
                                                           Identity)


@hookimpl
@singleton
def createEquipmentPlugin():
    return RFSwitch()


class RFSwitch(BaseCommsEquipment):
    def __init__(self):
        super().__init__("RF Switch")
        self.identity: Identity | None
        # Default communication parameters already provided by BaseEquipment (IP Address, Port, Timeout)
        # Override defaults specific to this switch if needed
        self.setParameterValue("Communication", "Port", 80)

    def initialise(self, init: Any | None = None) -> bool:
        # Allow user-provided init dict to override Communication params
        super().initialise(init)
        return True

    def getInfo(self) -> Any:
        return self._request("info")

    def switch(self, slot: int):
        logging.debug(f"Switching to RX:{slot}")
        if slot not in range(0, 5):
            logging.debug('Invalid slot number')
            raise ValueError('Slot must be between 0 and 4')

        relay_num = slot if slot > 0 else 1
        relay_val = 0 if slot == 0 else 1
        relay_cmd = f'cmd?Relay{relay_num}={relay_val}'

        self._request(relay_cmd)
        time.sleep(0.5)  # allow RF switch to settle

    # Internal request helper using communication parameters
    def _request(self, path: str) -> Any:
        ip = self.getParameterValue("Communication", "IP Address", "127.0.0.1")
        port = self.getParameterValue("Communication", "Port", 80)
        timeout_ms = self.getParameterValue("Communication", "Timeout", 5000)
        timeout_s = float(timeout_ms) / 1000.0

        url = f"http://{ip}:{int(port)}/{path}" if int(port) not in (80, 443) else f"http://{ip}/{path}"
        attempts = 0
        last_status: Any = None
        while attempts < 5:
            try:
                resp = requests.get(url, timeout=timeout_s)
                logging.debug(f"RF Switch request '{url}' status: {resp.status_code}")
                last_status = resp.status_code
                return resp.text if path == "info" else last_status

            except Exception as e:
                logging.debug(f"RF Switch request error: {e}")

            attempts += 1
            if attempts < 5:
                logging.debug("Retrying RF Switch connection...")

        logging.debug('Failed to connect to RF switch after retries')
        raise ConnectionError("RF Switch connection failed")
        raise ConnectionError("RF Switch connection failed")
