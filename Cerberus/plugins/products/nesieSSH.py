import logging
import time

from Cerberus.plugins.products.sshComms import SSHComms


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
