import logging
import pyvisa as visa

import common


class VISADevice():
    def __init__(self, port, ipAddress=None, timeout=10000):
        self.port = port
        self.timeout = timeout
        if ipAddress is None:
            self.ipAddress = "127.0.0.1"
        else:
            self.ipAddress = ipAddress

        self.resource = f'TCPIP::{self.ipAddress}::5025::SOCKET'

        self.rm = visa.ResourceManager()
        self.device = None

    def open(self):
        try:
            logging.debug(f"Opening VISA resource: {self.resource}")
            self.device = self.rm.open_resource(self.resource, read_termination='\n', write_termination='\n')
            self.device.timeout = self.timeout
            return self.device

        except Exception as e:
            logging.error(f"Failed to open resource: {self.resource} - {e}")
            return None

    def close(self) -> bool:
        if self.device is None:
            return True

        try:
            logging.debug(f"Closeing VISA resource: {self.resource}")
            self.device.close()
            return True

        except Exception as e:
            logging.error(f"Failed to close resource: {self.resource} - {e}")
            return False

    def write(self, command) -> bool:
        logging.trace(f"{self.resource} - Query {command}")
        if self.device is None:
            logging.warning("VISA Device is not open, can't write to device.")
            return False

        self.device.write(command)
        return True

    def query(self, command) -> str:
        logging.trace(f"{self.resource} - Query {command}")
        if self.device is None:
            logging.warning("VISA Device is not open, can't query the device.")
            return None

        return self.device.query(command)

    def operationComplete(self) -> bool:
        logging.trace(f"{self.resource} - *IDN?")
        resp = self.query("*IDN?")
        if resp is None:
            return False

        try:
            complete = int(resp)
            logging.trace(f"{self.resource} - *OPC? => {complete}")
            if complete != 0:
                return True
            else:
                return False

        except ValueError:
            logging.error(f"{self.resource} Invalid response from *OPC? [{resp}]")
            return False

    def reset(self, dwell=5):
        self.write("*RST?")
        common.dwell(dwell)

    def command(self, command) -> bool:
        if self.write(command):
            return self.operationComplete()
        else:
            return False
