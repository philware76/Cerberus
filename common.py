
import re
import time
from threading import Event


def dwell(period: float):
    period = time.perf_counter() + period
    while (time.perf_counter() < period):
        time.sleep(0.2)


def dwellStop(period: float, stopFunc=None):
    if stopFunc is None:
        dwell(period)
        return

    endTime = time.perf_counter() + period
    while (time.perf_counter() < endTime):
        time.sleep(0.2)
        if stopFunc():
            break


def dwellEvent(period: float, stopEvent: Event = None):
    if stopEvent is None:
        dwell(period)
        return

    endTime = time.perf_counter() + period
    while (time.perf_counter() < endTime):
        time.sleep(0.2)
        if stopEvent.wait(0.1):
            break


def camel2Human(name: str) -> str:
    # Add spaces before uppercase letters and capitalize the first letter
    human_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).capitalize()
    return human_name
