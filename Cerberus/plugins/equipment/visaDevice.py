import logging
from typing import cast

import pyvisa as visa
from pyvisa.resources.tcpip import TCPIPInstrument

from Cerberus import common
from Cerberus.exceptions import EquipmentError
from Cerberus.plugins.equipment.baseEquipment import Identity
from Cerberus.plugins.equipment.commsInterface import CommsInterface


class VISADevice(CommsInterface):
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

    def write(self, command: str):
        if self.instrument is None:
            raise EquipmentError("Instrument is not instantiated.")

        logging.debug(f"{self.resource} - Write {command}")
        if self.instrument.write(command) == 0:
            raise EquipmentError(f"Failed to send {command}")

    def query(self, command: str) -> str:
        if self.instrument is None:
            raise EquipmentError("Instrument is not instantiated.")

        logging.debug(f"{self.resource} - Query {command}")
        resp = self.instrument.query(command)

        logging.debug(f"{self.resource} - Response {resp}")
        return resp

    def operationComplete(self) -> bool:
        logging.debug("Waiting for operation complete...")
        self.write("*OPC")

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

    def reset(self, dwell=2):
        self.write("*RST")
        common.dwell(dwell)

    def command(self, command):
        self.write(command)
        return self.operationComplete()

    def identity(self) -> Identity:
        cmd = "*IDN?"
        idResp = self.query(cmd)
        if idResp is None:
            raise EquipmentError("Failed to get *IDN? response!")

        return Identity(idResp)
