import logging
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, Self

import requests

from Cerberus.cmdShells import common
from Cerberus.common import dwell


class PICStatusError(Exception):
    pass


class NesiePIC(dict[str, Any]):
    def __init__(self, host: str, *, timeout: tuple[float, float] = (10.0, 15.0)):
        super().__init__()
        self.url = "http://" + host.rstrip('/')          # base URL
        self.timeout = timeout              # (connect, read)
        self._session = requests.Session()
        self._session.trust_env = False     # ignore system proxies
        self._log = logging.getLogger(__name__)
        # initial status fetch
        self.status()

    @staticmethod
    def _convert(tag: str, text: str) -> Any:
        text = text.strip()
        if text == "":
            return None
        if tag in {"temperature", "fanspeed"}:
            try:
                return float(text)
            except ValueError:
                return text

        if tag.startswith("led") or tag == "PowerState":
            try:
                return int(text)
            except ValueError:
                return text
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return text

    def _get(self, path: str) -> requests.Response:
        url = f"{self.url}{path}"
        self._log.debug(f"NesiePIC GET {url} timeout={self.timeout}")
        try:
            r = self._session.get(url, timeout=self.timeout)
            r.raise_for_status()
            return r

        except requests.exceptions.ConnectTimeout as e:
            self._log.error(f"Connect timeout to {url} (connect={self.timeout[0]}s)")
            raise PICStatusError(f"Connect timeout: {e}") from e

        except requests.exceptions.ReadTimeout as e:
            self._log.error(f"Read timeout waiting response from {url} (read={self.timeout[1]}s)")
            raise PICStatusError(f"Read timeout: {e}") from e

        except requests.RequestException as e:
            self._log.error(f"HTTP error {url}: {e}")
            raise PICStatusError(f"HTTP error: {e}") from e

    def status(self) -> Self:
        r = self._get("/status.xml")
        try:
            root = ET.fromstring(r.text)

        except ET.ParseError as e:
            raise PICStatusError(f"XML parse error: {e}") from e

        if root.tag != "response":
            raise PICStatusError(f"Unexpected root tag: {root.tag}")

        parsed: Dict[str, Any] = {child.tag: self._convert(child.tag, child.text or "") for child in root}
        self.clear()
        self.update(parsed)

        return self

    def _power(self, onOff: int) -> bool:
        r = self._get(f"/update.cgi?PowerOn={onOff}")
        first_line = r.text.strip().splitlines()[0] if r.text else ""
        return first_line.startswith("Success!")

    def powerOn(self) -> bool:
        return self._power(1)

    def powerOff(self) -> bool:
        return self._power(0)

    def _waitForPowerState(self, state: int, continueFunc) -> bool:
        startTime = time.perf_counter()
        timeTaken = 0
        while continueFunc(timeTaken):
            self.status()
            if self["PowerState"] == state:
                return True

            time.sleep(2)
            timeTaken = time.perf_counter() - startTime

        return False

    def waitForPowerOn(self, func) -> bool:
        return self._waitForPowerState(8, func)

    def waitForPowerOff(self, func) -> bool:
        return self._waitForPowerState(0, func)
