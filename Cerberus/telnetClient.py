import logging
import telnetlib
from typing import Optional, Self


class TelnetError(Exception):
    """Base Telnet client exception."""


class TelnetTimeout(TelnetError):
    """Raised on read timeout."""


class TelnetProtocolError(TelnetError):
    """Raised when the device returns an error-indicating line (e.g. starts with 'ERR:')."""


class TelnetClient:
    """Small synchronous Telnet wrapper.

    Usage:
        client = TelnetClient(host, port, timeout=5.0)
        client.open()
        client.send("CMD")
        resp = client.query("IDN?")
        client.close()

    Not thread-safe. Create one instance per connection/thread.
    """

    def __init__(self, host: str, port: int, *, timeout: float = 120.0):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._tn: telnetlib.Telnet | None = None

    # ----------------------------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------------------------
    def open(self) -> None:
        if self._tn is not None:
            return
        logging.debug("TelnetClient: opening %s:%s (timeout=%s)", self._host, self._port, self._timeout)
        self._tn = telnetlib.Telnet(self._host, self._port, self._timeout)

    def close(self) -> None:
        if self._tn is not None:
            try:
                self._tn.close()
            finally:
                self._tn = None
                logging.debug("TelnetClient: closed %s:%s", self._host, self._port)

    # Context manager support ----------------------------------------------------------
    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # ----------------------------------------------------------------------------------
    # Core operations
    # ----------------------------------------------------------------------------------
    def _write(self, line: str) -> bool:
        """Send a line (appends newline)."""
        tn = self._require_open()
        data = (line + "\n").encode()
        logging.debug("-> %s", line)
        try:
            tn.write(data)

        except OSError as e:
            logging.error(f"Telnet Write Error: {e}")
            return False

        return True

    def send(self, line: str) -> bool:
        """Send a command and wait for the "\n" OK back"""
        if self._write(line):
            resp = self.read_line()
            return resp == ""
        else:
            return False

    def query(self, line: str, *, timeout: Optional[float] = None, strip: bool = True) -> str:
        """Send a line and read a single response line.

        timeout: overrides default timeout for this read only.
        strip: if True, rstrip CR/LF.
        """
        self._write(line)  # Don't use send()!!
        return self.read_line(timeout=timeout, strip=strip)

    def read_line(self, *, timeout: Optional[float] = None, strip: bool = True) -> str:
        tn = self._require_open()
        eff_timeout = timeout if timeout is not None else self._timeout
        raw = tn.read_until(b"\n", eff_timeout)
        if raw == b"":
            raise TelnetTimeout(f"Timeout reading line (>{eff_timeout}s)")

        text = raw.decode(errors="replace")
        if strip:
            text = text.rstrip("\r\n")

        logging.debug("<- %s", text)
        if text.startswith("ERR:"):
            raise TelnetProtocolError(text)

        return text

    # ----------------------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------------------
    def is_open(self) -> bool:
        return self._tn is not None

    def _require_open(self) -> telnetlib.Telnet:
        if self._tn is None:
            raise TelnetError("Connection not open")

        return self._tn
