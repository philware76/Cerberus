import logging
import socket
import time
from re import split

import paramiko

from Cerberus.plugins.products.bandNames import BandNames
from Cerberus.plugins.products.sshComms import SSHComms


class EEPROM:
    """Read/Write NESIE EEPROM data via SSH.

    Holds the last read lines and provides helpers to parse and update them.
    """

    READ_CMD = 'cd /opt/nesie/python/zynq-eeprom/ && python3 read_eeprom.py'
    WRITE_CMD = 'cd /opt/nesie/python/zynq-eeprom/ && python3 write_eeprom.py'
    EEPROM_TXT_PATH = '/opt/nesie/python/zynq-eeprom/eeprom_data.txt'

    def __init__(self, comms: SSHComms) -> None:
        self.ssh = comms
        self.lines: list[str] = []
        self.values: list[str] = []  # parsed 32-bit hex words from DATA=(...)

    # --- reading ---------------------------------------------------------------
    def read(self, *, display_stdout: bool = False) -> list[str]:
        ok, result = self.ssh.exec(self.READ_CMD, display_stdout=display_stdout)
        self.lines = result if isinstance(result, list) else [str(result)]

        values: list[str] = []
        if ok:
            # Find the response line and extract DATA=(...)
            for line in self.lines:
                if line.startswith("Response ") and "DATA=(" in line:
                    start = line.find("DATA=(") + len("DATA=(")
                    end = line.find(")", start)
                    if end != -1:
                        inner = line[start:end]
                        values = [tok.strip().lower().zfill(8) for tok in inner.split(',') if tok.strip()]
                    break

            if values:
                logging.debug("Read EEPROM OK")
            else:
                logging.debug("EEPROM response found but no DATA words parsed")
        else:
            logging.debug("Failed to read the EEPROM, or at least the SSH command failed.")

        self.values = values
        return values

    def get_token_line(self) -> str:
        for line in self.lines:
            if 'TOKEN=d000 LENGTH=041' in line:
                return line

        raise RuntimeError("Failed to read out token from EEPROM")

    @staticmethod
    def _convert_eeprom_hex(slots: list[int], slothex: str) -> None:
        slots.append(int(slothex[-2:], 16))
        slots.append(int(slothex[-4:-2], 16))
        slots.append(int(slothex[-6:-4], 16))
        slots.append(int(slothex[-8:-6], 16))

    def read_slots(self) -> list[int]:
        token = self.get_token_line()
        read_eeprom_response_list = split(r'\(|,|\)', token)
        slots03to00 = read_eeprom_response_list[62]  # MSByte is Slot 3
        slots07to04 = read_eeprom_response_list[63]  # MSByte is Slot 7
        slots11to08 = read_eeprom_response_list[64]  # MSByte is Slot 11
        slots15to12 = read_eeprom_response_list[65]  # MSByte is Slot 15

        slots: list[int] = []
        self._convert_eeprom_hex(slots, slots03to00)
        self._convert_eeprom_hex(slots, slots07to04)
        self._convert_eeprom_hex(slots, slots11to08)
        self._convert_eeprom_hex(slots, slots15to12)
        return slots

    # --- text file maintenance -------------------------------------------------
    def create_eeprom_txt_file(self) -> bool:
        """Ensure the on-device eeprom text file is readable and has non-empty data."""
        attempts = 0
        blank_hex = 'ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff'
        while attempts < 20:
            ok, out = self.ssh.exec(self.READ_CMD)
            if ok and any(blank_hex in line for line in out):
                logging.debug("EEPROM read confirmed")
                return True
            attempts += 1
            time.sleep(1)
        return False

    def update_text_file(self, hex_values: str, unit_type: str) -> bool:
        """Update the device text file with provided hex_values for the unit type."""
        try:
            with self.ssh.open_sftp() as sftp:
                with sftp.file(self.EEPROM_TXT_PATH, 'r') as f:  # type: ignore[attr-defined]
                    lines = f.readlines()
                    logging.debug(f"Previous EEPROM content: {lines[-2:]}")
                    lines[-1] = hex_values
                    if unit_type != 'Covert_A':
                        lines[-2] = hex_values
                with sftp.file(self.EEPROM_TXT_PATH, 'w') as f:  # type: ignore[attr-defined]
                    f.writelines(lines)
                logging.debug(f"New EEPROM content: {lines[-2:]}")
            return True
        except (paramiko.SSHException, paramiko.AuthenticationException, paramiko.BadHostKeyException) as e:
            logging.debug(f"ssh connection error: {e}")
        except (socket.timeout, socket.error) as e:
            logging.debug(f"ssh socket error: {e}")
        return False

    # --- programming -----------------------------------------------------------
    def program(self, hex_values: str, *, max_attempts: int = 5) -> bool:
        """Run the write_eeprom.py script until it reports the desired hex_values, up to max_attempts."""
        check = hex_values.strip()
        attempts = 0
        while attempts < max_attempts:
            logging.debug(f"Attempting to write to eeprom ({attempts/max_attempts})...")
            ok, out = self.ssh.exec(self.WRITE_CMD)
            if ok and any(check in line for line in out):
                logging.debug("EEPROM Write confirmed!")
                return True
            logging.debug("Failed to program eeprom via write_eeprom.py ssh script")
            attempts += 1
            time.sleep(1)
        return False


class FittedBands:
    """Helper to determine fitted bands from EEPROM 32-bit word values.

    Usage:
        bands = FittedBands.bands(values, slot_details, filters)
    where
        - values: list[str] from EEPROM.read() (each an 8-hex-digit string)
        - slot_details: mapping of slot index -> default band (first 7 slots may supply defaults)
        - filters: mapping of filter code (int) -> band (Band enum)
    """

    @staticmethod
    def _bytes_from_word(word: str) -> list[int]:
        w = word.strip().lower().zfill(8)[-8:]
        return [int(w[-2:], 16), int(w[-4:-2], 16), int(w[-6:-4], 16), int(w[-8:-6], 16)]

    @classmethod
    def _slots_from_values(cls, values: list[str], filters: dict[int, BandNames]) -> list[int]:
        if not values:
            return []

        # Convert each 32-bit word into 4 bytes (LSB..MSB) and slide a 4-word window to get 16 slots
        candidate: list[int] | None = None
        filter_keys = set(filters.keys())

        for i in range(0, max(0, len(values) - 3)):
            window = values[i:i+4]
            bytes16: list[int] = []
            for w in window:
                bytes16.extend(cls._bytes_from_word(w))
            # Heuristic: prefer windows that contain at least one known filter code
            if any(b in filter_keys for b in bytes16):
                candidate = bytes16

        # Fallback to the last 4 words if nothing matched
        if candidate is None:
            bytes16 = []
            for w in values[-4:]:
                bytes16.extend(cls._bytes_from_word(w))
            candidate = bytes16

        return candidate

    @classmethod
    def bands(cls, values: list[str], slot_details: dict[int, BandNames], filters: dict[int, BandNames]) -> list[BandNames]:
        slots = cls._slots_from_values(values, filters)
        if not slots:
            return []

        ST = len(slot_details)
        reverse_filter: dict[BandNames, int] = {v: k for k, v in filters.items()}

        # Apply default mapping for first 7 slots when value is 0xff
        converted: list[int] = []
        for i, x in enumerate(slots[:ST]):
            if i <= 6 and x == 0xFF:
                default_band = slot_details.get(i)
                code = reverse_filter.get(default_band) if default_band is not None else None
                converted.append(code if code is not None else 0xFF)
            else:
                converted.append(x)

        # Map codes to bands, ignore unknowns/0xff
        result: list[BandNames] = []
        for i, code in enumerate(converted):
            if i >= ST:
                break
            band = filters.get(code)
            if band:
                result.append(band)
        return result
