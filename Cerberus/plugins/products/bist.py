import logging
from typing import Protocol, runtime_checkable

from Cerberus.telnetClient import TelnetClient, TelnetError


@runtime_checkable
class _BISTIO(Protocol):
    def _send(self,  cmd: str) -> None: ...
    def _query(self,  cmd: str) -> str: ...


# Exception hierarchy -----------------------------------------------------------------
class BISTError(Exception):
    """Base exception for all BIST related errors."""


class BISTNotInitializedError(BISTError):
    """Raised when an operation requires an open / initialised connection."""


class BISTConnectionError(BISTError):
    """Raised on failures opening or maintaining the underlying telnet connection."""


class BISTQueryError(BISTError):
    """Raised when a query/command fails or returns an unexpected response."""


class BISTProtocolError(BISTError):
    """Raised when low level BIST protocol / handshake response is invalid."""


class BaseBIST(_BISTIO):
    def __init__(self):
        logging.debug("__init__")
        self._client: TelnetClient | None = None
        self.bistHost: str | None = None

    def initComms(self,  host: str, port: int = 51234, timeout: float = 120.0):
        self.bistHost = host
        self._client = TelnetClient(host, port, timeout=timeout)

    def openBIST(self):
        if self._client is None:
            raise BISTNotInitializedError("initComms must be called before openBIST().")

        try:
            self._client.open()
            logging.debug("Waiting for OK back after opening telnet connection...")
            # Some firmware expects an empty CR/LF to emit a prompt / OK - ignore errors quietly.
            try:
                self._query("TX:ENAB?")
            except BISTQueryError:
                pass

        except TelnetError as e:
            raise BISTConnectionError(f"Failed to open BIST connection: {e}") from e

    def closeBIST(self):
        if self._client:
            self._client.close()

    def is_open(self):
        return bool(self._client and self._client.is_open())

    def _send(self,  cmd: str):
        if not self.is_open():
            raise BISTNotInitializedError("Telnet to BIST has not been opened yet.")

        try:
            self._client.send(cmd)  # type: ignore[union-attr]

        except TelnetError as e:
            raise BISTConnectionError(f"Send failed: {cmd}: {e}") from e

    def _query(self,  cmd: str) -> str:
        if not self.is_open():
            raise BISTNotInitializedError("Telnet to BIST has not been opened yet.")

        try:
            return self._client.query(cmd).strip()  # type: ignore[union-attr]

        except TelnetError as e:
            raise BISTConnectionError(f"Query failed: {cmd}: {e}") from e

        except Exception as e:  # defensive
            raise BISTQueryError(f"Unexpected error during query '{cmd}': {e}") from e

# Feature mixins --------------------------------------------------


class TxControlMixin:
    def set_tx_enable(self: _BISTIO): self._send("TX:ENAB")
    def set_tx_disable(self: _BISTIO): self._send("TX:DISA")
    def get_tx_enabled(self: _BISTIO): return self._query("TX:ENAB?")


class PaMixin:
    PA_MAP = {
        "low": "PA_LOW",
        "high": "PA_HIGH",
        "3ghz": "PA_3GHZ",
    }
    def get_pa_path(self: _BISTIO): return self._query("TX:PAPATH?")

    def set_pa_on(self: _BISTIO,  path: str):
        self._send(f"TX:PAPATH {path}")
        self._send(f"TX:PAEN {path}")

    def set_pa_off(self: _BISTIO):
        self._send("TX:PAEN PA_OFF")
        self._send("TX:PAPATH PA_OFF")


class AttenuationMixin:
    def set_attn(self: _BISTIO,  value: int): self._send(f"TX:ATTN {value}")
    def get_attn(self: _BISTIO): return self._query("TX:ATTN?")


class TxFreqMixin:
    def set_tx_freq(self: _BISTIO,  mhz: float): self._send(f"TX:FREQ {int(mhz*1e6)}")
    def get_tx_freq(self: _BISTIO): return self._query("TX:FREQ?")


class TsSignalMixin:
    def set_ts_on(self: _BISTIO): self._send("TX:TS:ENAB")
    def set_ts_off(self: _BISTIO): self._send("TX:TS:DISA")
    def set_ts_freq_set(self: _BISTIO,  mhz: float): self._send(f"TX:TS:FREQ {int(mhz*1e6)}")
    def get_ts_freq_get(self: _BISTIO): return self._query("TX:TS:FREQ?")


class RxControlMixin:
    def get_rx_freq(self: _BISTIO): return self._query("RX:FREQ?")
    def set_set_rx_freq(self: _BISTIO,  mhz: float): self._send(f"RX:FREQ {int(mhz*1e6)}")
    def get_rx_gain(self: _BISTIO): return self._query("RX:GAIN?")
    def set_rx_gain(self: _BISTIO,  gain: int): self._send(f"RX:GAIN {gain}")


class BandwidthMixin:
    def get_rx_bw(self: _BISTIO): return self._query("RX:BW?")
    def set_rx_bw(self: _BISTIO,  mhz: float): self._send(f"RX:BW {int(mhz*1e6)}")
    def get_tx_bw(self: _BISTIO): return self._query("TX:BW?")
    def set_tx_bw(self: _BISTIO,  mhz: float): self._send(f"TX:BW {int(mhz*1e6)}")


class DuplexerMixin:
    DUP_NAMES_TX = [...]  # fill from PDF
    DUP_NAMES_RX = [...]
    def get_duplex(self: _BISTIO,  side: str): return self._query(f"{side}:DUP?")
    def set_duplex(self: _BISTIO,  side: str, code: str): self._send(f"{side}:DUP {code}")


class TempsMixin:
    def get_temps(self: _BISTIO):
        def _flt(s: str): import re; m = re.findall(r"[0-9.]+", s); return float(m[0]) if m else float('nan')
        da = _flt(self._query("DA:TEMP?"))
        rf = _flt(self._query("ENG:TEMP?"))
        pa = _flt(self._query("TX:PATEMP?"))
        mb = _flt(self._query("ENG:TEMP? MB"))
        return da, rf, pa, mb


class LTEWaveformMixin:
    def cmd_lteStart(self: _BISTIO,  freq_mhz: float):
        dm = int(round(freq_mhz*10))
        self._send("APP:NESIERF:CLOSEDLOOPPWRCTL ENABLE")
        self._send("APP:NESIERF:LIMITER 0")
        self._send("APP:NESIERF:ATTN 15 0")
        self._send(f"APP:NESIERF:TX {dm} 400 NOHUP")

    def cmd_lteStop(self: _BISTIO):
        self._send("APP:NESIERF:OFF")

# Device variants -------------------------------------------------


class TacticalBIST(BaseBIST, TxControlMixin, PaMixin, AttenuationMixin,
                   TxFreqMixin, TsSignalMixin, RxControlMixin,
                   BandwidthMixin, DuplexerMixin, TempsMixin, LTEWaveformMixin):
    """Collection of BIST commands (mixins) for Tactical"""
    pass


class CovertBIST(BaseBIST, TxControlMixin, TxFreqMixin, RxControlMixin, TempsMixin):
    """Collection of BIST commands (mixins) for Covert"""
    pass


class StrategicBIST(BaseBIST, TxControlMixin, PaMixin, TxFreqMixin, RxControlMixin,
                    BandwidthMixin, TempsMixin, LTEWaveformMixin):
    """Collection of BIST commands (mixins) for Strategic"""
    pass
