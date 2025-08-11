import logging
import time
from typing import cast

import pyvisa as visa
from pyvisa.resources.tcpip import TCPIPInstrument

from Cerberus import common
from Cerberus.exceptions import EquipmentError
from Cerberus.plugins.equipment.baseEquipment import Identity


class VISADevice():
    def __init__(self, port, ipAddress=None, timeout=10000):
        self.port = port
        self.timeout = timeout
        if ipAddress is None:
            self.ipAddress = "127.0.0.1"
        else:
            self.ipAddress = ipAddress

        # Use the provided port instead of hard-coded 5025
        self.resource = f'TCPIP::{self.ipAddress}::{self.port}::SOCKET'

        self.rm = visa.ResourceManager()
        self.instrument: TCPIPInstrument | None = None

    def open(self) -> TCPIPInstrument | None:
        try:
            logging.debug(f"Opening VISA resource: {self.resource}")
            resource = self.rm.open_resource(self.resource, read_termination='\n', write_termination='\n')
            self.instrument = cast(TCPIPInstrument, resource)

            logging.debug(self.instrument)
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

    def checkSend(self, cmd) -> bool:
        if self.instrument is None:
            print("Device needs to be initialised with 'init' command")
            return False

        if not self.command(cmd):
            logging.debug(f"Command {cmd} was not successful.")
            return False

        return True

    def write(self, command: str) -> bool:
        logging.debug(f"{self.resource} - Write {command}")
        if self.instrument is None:
            logging.warning("VISA Device is not open, can't write to device.")
            return False

        self.instrument.write(command)
        return True

    def query(self, command: str) -> str | None:
        logging.debug(f"{self.resource} - Query {command}")
        if self.instrument is None:
            logging.warning("VISA Device is not open, can't query the device.")
            return None

        return self.instrument.query(command)

    def operationComplete(self) -> bool:
        logging.debug("Waiting for operation complete...")
        if not self.write("*OPC"):
            logging.warning("Failed to send *OPC")
            return False

        count = 0
        while count < 10:
            resp = self.query("*ESR?")
            if resp is None:
                logging.debug("Failed to get response from *ESR?")
                return False

            try:
                complete = int(resp)
                logging.debug(f"{self.resource} - *ESR? => {complete}")
                if complete == 1:
                    return True
                else:
                    common.dwell(0.1)
                    count += 1

            except ValueError:
                logging.error(f"{self.resource} Invalid response from *ESR? [{resp}]")
                return False

        raise EquipmentError("Failed to get operation complete")

    def reset(self, dwell=5):
        self.write("*RST")
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
