import logging
import os
import socket
import time
from re import split

import paramiko


class SSHComms:
    """Thin wrapper around paramiko SSHClient with simple exec and SFTP helpers.

    Usage:
        ssh = SSHComms(host)
        ssh.open_with_key(<key_path>)  # or open_with_password('password')
        ok, out = ssh.exec('uptime')
        ssh.close()
    """

    def __init__(self, host: str, *, username: str = 'root', password: str | None = None,
                 key_path: str | os.PathLike | None = None, timeout: float = 30.0) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.key_path = str(key_path) if key_path is not None else None
        self.timeout = timeout
        self._client: paramiko.SSHClient | None = None

    # Context manager support
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # --- connection management -------------------------------------------------
    def _ensure_client(self) -> paramiko.SSHClient:
        if self._client is None:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client = client
        return self._client

    def is_open(self) -> bool:
        if not self._client:
            return False
        transport = self._client.get_transport()
        return bool(transport and transport.is_active())

    def open(self) -> None:
        """Open using provided password or key_path (if set)."""
        if self.is_open():
            return

        if self.key_path:
            self.open_with_key(self.key_path)

        else:
            self.open_with_password(self.password or '')

    def open_with_key(self, key_path: str | os.PathLike, *, disabled_algorithms: dict | None = None) -> None:
        client = self._ensure_client()
        key = paramiko.RSAKey.from_private_key_file(str(key_path))

        try:
            client.connect(
                self.host,
                username=self.username,
                pkey=key,
                timeout=self.timeout,
                disabled_algorithms=disabled_algorithms or {'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']},
            )

        except Exception as e:
            raise RuntimeError(f"Failed to connect SSH to {self.host} with key: {e}") from e

    def open_with_password(self, password: str, *, disabled_algorithms: dict | None = None) -> None:
        client = self._ensure_client()

        try:
            client.connect(
                self.host,
                username=self.username,
                password=password,
                timeout=self.timeout,
                disabled_algorithms=disabled_algorithms or {'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']},
            )

        except Exception as e:
            raise RuntimeError(f"Failed to connect SSH to {self.host} with password: {e}") from e

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()

            finally:
                self._client = None

    # --- command execution -----------------------------------------------------
    def exec(self, command: str, *, display_stdout: bool = False, display_stderr: bool = True) -> tuple[bool, list[str]]:
        """Execute a command. Returns (success, lines). Lines are stdout if success, else stderr."""
        if not self.is_open():
            raise RuntimeError("SSHComms.exec() called before connection is open")

        try:
            _, ssh_stdout, ssh_stderr = self._client.exec_command(command)  # type: ignore[union-attr]
            stdout_text = ssh_stdout.read().decode('utf-8', errors='replace')
            stderr_text = ssh_stderr.read().decode('utf-8', errors='replace')
            stdout = [line.strip() for line in stdout_text.split('\n') if line.strip()]
            stderr = [line.strip() for line in stderr_text.split('\n') if line.strip()]

            if stdout and display_stdout:
                for line in stdout:
                    logging.debug(line)

            if stderr:
                if display_stderr:
                    for line in stderr:
                        logging.debug(f"ssh command error: {line}")
                return False, stderr

            return True, stdout

        except (paramiko.SSHException, paramiko.AuthenticationException, paramiko.BadHostKeyException) as e:
            msg = f"ssh connection error: {e}"
            logging.debug(msg)
            return False, [msg]

        except (socket.timeout, socket.error) as e:
            msg = f"ssh socket error: {e}"
            logging.debug(msg)
            return False, [msg]

    # --- SFTP helpers ----------------------------------------------------------
    def open_sftp(self) -> paramiko.SFTPClient:
        if not self.is_open():
            raise RuntimeError("SSHComms.open_sftp() called before connection is open")

        return self._client.open_sftp()  # type: ignore[union-attr]

    def read_file(self, remote_path: str) -> list[str]:
        with self.open_sftp() as sftp:
            with sftp.file(remote_path, 'r') as f:  # type: ignore[attr-defined]
                data = f.read().decode('utf-8', errors='replace')
                return [line for line in (l.strip() for l in data.split('\n')) if line]

    def write_file(self, remote_path: str, content: list[str] | str) -> None:
        text = ''.join(content) if isinstance(content, list) else content
        with self.open_sftp() as sftp:
            with sftp.file(remote_path, 'w') as f:  # type: ignore[attr-defined]
                f.write(text)


class NesieSSH:
    """NESIE-related SSH helpers using SSHComms for transport."""

    def __init__(self, comms: SSHComms) -> None:
        self.ssh = comms

    def run(self, command: str, *, display_stdout: bool = False, display_stderr: bool = True) -> tuple[bool, list[str]]:
        return self.ssh.exec(command, display_stdout=display_stdout, display_stderr=display_stderr)

    def kill_nesie(self) -> tuple[bool, list[str]]:
        return self.run('killall nesie-daemon', display_stdout=False)

    def stop_daemon(self) -> bool:
        ok, out = self.run('/etc/init.d/nesie-daemon stop', display_stderr=False)
        if ok:
            logging.debug("NESIE-daemon is stopped")
            return True

        if any("already stopped" in line for line in out):
            logging.debug("NESIE-daemon was already stopped")
            return True

        logging.debug("Failed to stop NESIE-daemon")
        logging.debug(str(out))

        return False

    def uptime_seconds(self) -> int | None:
        ok, out = self.run('uptime')
        if not ok or not out:
            logging.debug("Unable to read uptime")
            return None

        # Preserve legacy parsing behavior
        line = out[0]
        try:
            idx = line.index("up")
            uptime = line[:idx].split(':')
            return int(uptime[0]) * 60 * 60 + int(uptime[1]) * 60 + int(uptime[2])

        except Exception:
            return None

    def wait_for_uptime(self, *, wait_uptime: int = 60) -> bool:
        secs = self.uptime_seconds()
        if secs is None:
            return False

        logging.debug(f"OCXO warm up time check - Device uptime is {secs} seconds")
        if secs < wait_uptime:
            wait_time = wait_uptime - secs
            logging.debug(f"Waiting for {wait_time} for OCXO to warm up at least 60 seconds")
            time.sleep(wait_time)

        return True

    # --- added helpers --------------------------------------------------------
    def check_unit_version(self) -> tuple[str, str] | tuple[None, None]:
        """Return (/etc/version without dots, raw line) or (None, None) on failure."""
        ok, out = self.run('cat /etc/version')
        if not ok or not out:
            return None, None

        raw = out[0].strip()
        return raw.replace('.', ''), raw

    def check_unit_srn(self, unit_type: str) -> str | None:
        """Return unit serial number string or None on failure."""
        match unit_type:
            case 'Tactical_U' | 'Tactical_G':
                cmd = 'cat /etc/serial-trx'
            case 'Covert_A' | 'Strategic_A':
                cmd = 'cat /etc/serial.assembly'
            case _:
                cmd = 'cat /etc/serial.assembly'  # default/fallback

        ok, out = self.run(cmd)
        return out[0].strip() if ok and out else None


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

    # --- reading ---------------------------------------------------------------
    def read(self, *, display_stdout: bool = False) -> bool:
        ok, result = self.ssh.exec(self.READ_CMD, display_stdout=display_stdout)
        self.lines = result if isinstance(result, list) else [str(result)]
        if ok:
            logging.debug("Read EEPROM OK")
        else:
            logging.debug("Failed to read the EEPROM, or at least the SSH command failed.")
        return ok

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

    def unit_hex_values(self) -> list[str]:
        logging.debug('\nInterrogating Unit For Available Bands...')
        slots = self.read_slots()
        return [hex(i) for i in slots]

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
