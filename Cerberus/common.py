import re
import time
import zlib
from dataclasses import dataclass
from threading import Event
from typing import Optional


@dataclass
class DBInfo:
    host: str = "localhost"
    port: int = 3306
    username: str = "root"
    password: str = ""
    database: str = "cerberus"


class Spinner:
    def __init__(self, chars=None):
        if chars is None:
            chars = ['', '.', '..', '...', '....', '.....']

        self.chars = chars
        self.index = 0

    def next(self):
        char = self.chars[self.index]
        self.index = (self.index + 1) % len(self.chars)  # Cycle through indices
        return char


def dwell(period: float):
    period = time.perf_counter() + period
    while (time.perf_counter() < period):
        time.sleep(0.1)


def dwellStop(period: float, stopFunc=None):
    if stopFunc is None:
        dwell(period)
        return

    endTime = time.perf_counter() + period
    while (time.perf_counter() < endTime):
        time.sleep(0.1)
        if stopFunc():
            break


def dwellEvent(period: float, stopEvent: Optional[Event] = None):
    if stopEvent is None:
        dwell(period)
        return

    endTime = time.perf_counter() + period
    while (time.perf_counter() < endTime):
        if stopEvent.wait(0.1):
            break


def calcCRC(plan: object) -> int:
    """Deterministic CRC based only on Plan test entries.
    Order-insensitive, counts matter; returns 0 if plan is None or not iterable.
    """
    if plan is None:
        return 0
    try:
        tests = [str(t) for t in plan]  # type: ignore[arg-type]
    except Exception:
        return 0
    tests_sorted = sorted(tests)
    payload = ("|".join(tests_sorted) + f"#{len(tests_sorted)}").encode("utf-8")
    return zlib.crc32(payload) & 0xFFFFFFFF


def camel2Human(name: str) -> str:
    # Add spaces before uppercase letters and capitalize the first letter
    humanReadable = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).capitalize()
    return humanReadable
