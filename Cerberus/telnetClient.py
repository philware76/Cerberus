import logging
import socket
import time
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
        self._sock: socket.socket | None = None
        self._buffer = b""

    # ----------------------------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------------------------
    def open(self) -> None:
        if self._sock is not None:
            return
        logging.debug("TelnetClient: opening %s:%s (timeout=%s)", self._host, self._port, self._timeout)
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self._timeout)
            self._sock.connect((self._host, self._port))
            self._buffer = b""
        except (socket.error, OSError) as e:
            if self._sock:
                self._sock.close()
                self._sock = None
            raise TelnetError(f"Failed to connect to {self._host}:{self._port}: {e}")

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None
                self._buffer = b""
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
        sock = self._require_open()
        data = (line + "\n").encode()
        logging.debug("-> %s", line)
        try:
            sock.sendall(data)
        except (socket.error, OSError) as e:
            raise TelnetError(f"Telnet Write Error: {e}")
        return True

    def send(self, line: str) -> bool:
        """Send a command and wait for the "\n" OK back"""
        if self._write(line):
            resp = self.read_line(strip=False)
            return resp.startswith("\n")
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
        sock = self._require_open()
        eff_timeout = timeout if timeout is not None else self._timeout

        # Set timeout for this operation
        original_timeout = sock.gettimeout()
        sock.settimeout(eff_timeout)

        try:
            # Look for existing newline in buffer
            while b"\n" not in self._buffer:
                try:
                    data = sock.recv(1024)
                    if not data:
                        raise TelnetTimeout(f"Connection closed while reading line")
                    self._buffer += data
                except socket.timeout:
                    raise TelnetTimeout(f"Timeout reading line (>{eff_timeout}s)")
                except (socket.error, OSError) as e:
                    raise TelnetError(f"Socket error while reading: {e}")

            # Extract line from buffer
            newline_pos = self._buffer.find(b"\n")
            line_data = self._buffer[:newline_pos + 1]
            self._buffer = self._buffer[newline_pos + 1:]

            text = line_data.decode(errors="replace")
            if strip:
                text = text.rstrip()

            if text.startswith("ERR:"):
                raise TelnetProtocolError(text)

            if text != "":
                logging.debug("<- '%s'", text)

            return text

        finally:
            # Restore original timeout
            sock.settimeout(original_timeout)

    # ----------------------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------------------
    def is_open(self) -> bool:
        return self._sock is not None

    def _require_open(self) -> socket.socket:
        if self._sock is None:
            raise TelnetError("Connection not open")
        return self._sock
