import logging
import time
from typing import Any

import requests

from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment, Identity


@hookimpl
@singleton
def createEquipmentPlugin():
    return RFSwitch()


class RFSwitch(BaseEquipment):
    def __init__(self):
        super().__init__("RF Switch")
        self.identity: Identity | None

        self._init = {"Port": 80, "IPAddress": "127.0.0.1"}

    def getInfo(self):
        info = self.request("info")
        if info is not None:
            logging.debug(info)

        return info

    def Switch(self, slot):
        logging.debug(f"Switching to RX:{slot}")
        if slot not in range(0, 5):
            logging.debug('Invalid slot number')
            raise ValueError('Slot must be between 0 and 4')

        relay_num = slot if slot > 0 else 1
        relay_val = 0 if slot == 0 else 1
        relay_cmd = f'cmd?Relay{relay_num}={relay_val}'

        self.request(relay_cmd)

        # dwell for rf switch to settle.
        time.sleep(0.5)

    def request(self, relay_cmd):
        get_request = None
        attm = 0
        while get_request is None and attm < 5:
            try:
                req = requests.get(f'http://{switch_ip}/{relay_cmd}', timeout=10)
                logging.debug(f"Status Code: {req.status_code}")
                get_request = req.status_code
            except Exception as e:
                logging.debug(e)
                pass

            if get_request is None:
                logging.debug('Failed to connect to RF switch retrying!')
                attm += 1

        if get_request is None:
            logging.debug('Failed to connect to RF switch')
            raise Exception
