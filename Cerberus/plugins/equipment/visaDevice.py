from logging import INFO
from typing import cast

import pyvisa as visa
from pyvisa.resources.tcpip import TCPIPInstrument

from Cerberus import common
from Cerberus.exceptions import EquipmentError
from Cerberus.logConfig import getLogger
from Cerberus.plugins.equipment.baseEquipment import Identity
from Cerberus.plugins.equipment.commsInterface import CommsInterface

logger = getLogger("VISA")
logger.setLevel(INFO)


class VISADevice(CommsInterface):
    OPC_DWELL_TIME = 0.2

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
            logger.debug("Opening VISA resource: %s", self.resource)
            resource = self.rm.open_resource(self.resource, read_termination='\n', write_termination='\n')
            self.instrument = cast(TCPIPInstrument, resource)

            logger.debug(self.instrument)
            self.instrument.timeout = self.timeout

            return self.instrument

        except (visa.errors.VisaIOError, Exception) as e:
            logger.error("Failed to open resource: %s - %s", self.resource, e)
            return None

    def close(self) -> bool:
        if self.instrument is None:
            return True

        try:
            logger.debug("Closing VISA resource: %s", self.resource)
            self.instrument.close()
            return True

        except (visa.errors.VisaIOError, Exception) as e:
            logger.error("Failed to close resource: %s - %s", self.resource, e)
            return False

    def write(self, command: str):
        if self.instrument is None:
            raise EquipmentError("Instrument is not instantiated.")

        logger.debug("%s - Write %s", self.resource, command)
        try:
            if self.instrument.write(command) == 0:
                raise EquipmentError(f"Failed to send '{command}'")

        except visa.errors.VisaIOError as e:
            raise EquipmentError(f"Failed to send '{command}'") from e

    def read(self, bytes: int) -> str:
        if self.instrument is None:
            raise EquipmentError("Instrument is not instantiated.")

        logger.debug("%s - Read...", self.resource)
        try:
            resp = repr(self.instrument.read_bytes(bytes))

        except visa.errors.VisaIOError as e:
            raise EquipmentError(f"Failed to read from device'") from e

        logger.debug("%s - Response: %s", self.resource, resp)
        return resp

    def query(self, command: str) -> str:
        if self.instrument is None:
            raise EquipmentError("Instrument is not instantiated.")

        logger.debug("%s - Query: %s", self.resource, command)
        try:
            resp = self.instrument.query(command)

        except visa.errors.VisaIOError as e:
            raise EquipmentError(f"Failed to query '{command}'") from e

        logger.debug("%s - Response: %s", self.resource, resp)
        return resp

    def operationComplete(self) -> bool:
        logger.debug("Waiting for operation complete...")

        resp = self.query("*OPC?")
        if resp is None:
            logger.debug("Failed to get response from *OPC?")
            return False

        try:
            complete = int(resp)
            logger.debug("%s - *OPC? => %s", self.resource, complete)
            if complete == 1:
                return True

        except ValueError:
            logger.error("%s Invalid response from *OPC? [%s]", self.resource, resp)
            return False

        raise EquipmentError("Failed to get operation complete")

    def reset(self, dwell=2):
        self.write("*RST")
        common.dwell(dwell)

    def command(self, command):
        self.write(command)
        return self.operationComplete()

    def getIdentity(self) -> Identity:
        cmd = "*IDN?"
        idResp = self.query(cmd)
        if idResp is None:
            raise EquipmentError("Failed to get *IDN? response!")

        return Identity(idResp)

    def drain(self) -> int:
        """Discard any pending data in the VISA read buffer.

        Returns number of bytes discarded (best-effort). If instrument handle
        not open, returns 0.
        """
        if self.instrument is None:
            return 0
        # Attempt to read until timeout using a short temporary timeout
        import pyvisa
        from pyvisa import constants, errors
        inst = self.instrument
        # First flush driver buffer (host side)
        try:
            # Pylance/mypy may not match literal -> BufferOperation; cast safely
            inst.flush(constants.VI_READ_BUF_DISCARD)  # type: ignore[arg-type]
        except Exception:
            pass
        original = inst.timeout
        inst.timeout = 200  # ms
        discarded = 0
        try:
            while True:
                try:
                    chunk = inst.read_raw()  # may timeout
                    if not chunk:
                        break
                    discarded += len(chunk)
                except errors.VisaIOError as e:
                    if e.error_code == constants.VI_ERROR_TMO:
                        break
                    else:
                        break
        finally:
            inst.timeout = original

        logger.debug("%s - Drained %s bytes from buffer", self.resource, discarded)
        return discarded
