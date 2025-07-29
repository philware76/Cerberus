import logging

import common
import pyvisa as visa

from Cerberus.plugins.equipment.baseEquipment import Identity


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
        self.instrument = None

    def open(self):
        try:
            logging.debug(f"Opening VISA resource: {self.resource}")
            self.instrument = self.rm.open_resource(self.resource, read_termination='\n', write_termination='\n')
            print(self.instrument)
            self.instrument.timeout = self.timeout
            return self.instrument

        except Exception as e:
            logging.error(f"Failed to open resource: {self.resource} - {e}")
            return None

    def close(self) -> bool:
        if self.instrument is None:
            return True

        try:
            logging.debug(f"Closeing VISA resource: {self.resource}")
            self.instrument.close()
            return True

        except Exception as e:
            logging.error(f"Failed to close resource: {self.resource} - {e}")
            return False

    def write(self, command) -> bool:
        logging.debug(f"{self.resource} - Query {command}")
        if self.instrument is None:
            logging.warning("VISA Device is not open, can't write to device.")
            return False

        self.instrument.write(command)
        return True

    def query(self, command) -> str | None:
        logging.debug(f"{self.resource} - Query {command}")
        if self.instrument is None:
            logging.warning("VISA Device is not open, can't query the device.")
            return None

        return self.instrument.query(command)

    def operationComplete(self) -> bool:
        logging.debug(f"{self.resource} - *OPC?")
        resp = self.query("*OPC?")
        if resp is None:
            return False

        try:
            complete = int(resp)
            logging.debug(f"{self.resource} - *OPC? => {complete}")
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

    def identity(self) -> Identity | None:
        cmd = "*IDN?"
        idResp = self.query(cmd)
        if idResp is None:
            return None

        return Identity(idResp)
