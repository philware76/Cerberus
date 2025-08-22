import pathlib
import time
from time import sleep

import numpy as np
import pyvisa as visa

# Define the variables
freqStart = int(2.3e9)
freqStop = int(2.7e9)
freqSpacing = int(1e6)
freqStep = int(((freqStop - freqStart)/freqSpacing)+1)
freq = np.linspace(freqStart, freqStop, freqStep)
pwrLevel = np.linspace(0, 1, 1)

timeStr = time.strftime("%Y%m%d_%H%M%S")
PCFile = pathlib.Path(r"c:/temp/"+timeStr+r'.csv')


class Instrument:
    """Simplified SMB100A + NRP sensor control using pyvisa.

    Reimplements only the subset of RsInstrument functionality used in the
    original script (write_str_with_opc, query_str / query_float).
    """

    def __init__(self, ip_address: str, timeout_ms: int = 10000):
        self.ip_address = ip_address
        self.timeout_ms = timeout_ms
        self.devNum: int | None = None
        self.rm: visa.ResourceManager | None = None
        self.instrument = None

    # ---------- Low-level helpers ----------
    def _resource_string(self) -> str:
        # Raw socket fallback (R&S default SCPI port 5025)
        return f"TCPIP::{self.ip_address}::5025::SOCKET"

    def open(self):
        """Open VISA session, perform ID query, clear status, reset."""
        self.rm = visa.ResourceManager()
        res = self._resource_string()
        self.instrument = self.rm.open_resource(res, read_termination='\n', write_termination='\n')  # type: ignore[assignment]

        # Configure timeout (ms)
        try:  # type: ignore[attr-defined]
            self.instrument.timeout = self.timeout_ms  # type: ignore[attr-defined]
        except Exception:
            pass

        # Perform ID query + reset like RsInstrument (guarded)
        idn = self.query_str("*IDN?").strip()
        print(f"*IDN? => {idn}")

        # Clear & reset (separate *CLS then *RST + OPC wait)
        self.write("*CLS")
        self.write_opc("*RST")

    def close(self):
        if self.instrument:
            try:
                self.write_opc('SOURce:POWer:LEVel:IMMediate:AMPLitude -100')

            except Exception:
                pass

            self.instrument.close()

        if self.rm:
            try:
                self.rm.close()

            except Exception:
                pass

    # ---------- SCPI convenience ----------
    def write(self, cmd: str):
        if not self.instrument:
            raise RuntimeError("Instrument not opened")

        inst = self.instrument  # type: ignore[assignment]
        inst.write(cmd)  # type: ignore[attr-defined]

    def query_str(self, cmd: str) -> str:
        if not self.instrument:
            raise RuntimeError("Instrument not opened")

        inst = self.instrument  # type: ignore[assignment]
        return inst.query(cmd).strip()  # type: ignore[attr-defined]

    def query_float(self, cmd: str) -> float:
        return float(self.query_str(cmd))

    def write_opc(self, cmd: str, timeout_ms: int | None = None) -> None:
        self.write(cmd)
        # Optionally override timeout temporarily for long operations
        inst = self.instrument
        assert inst is not None

        prev = inst.timeout
        if timeout_ms is not None:
            inst.timeout = timeout_ms

        try:
            resp = self.query_str("*OPC?")
            if resp != '1':
                raise RuntimeError(f"*OPC? returned {resp} (expected 1)")

        finally:
            inst.timeout = prev

    # ---------- High-level logic ----------
    def comprep(self):
        # Already did clear/reset in open; replicate remaining settings
        # (OPC timeout emulation done per call in write_opc)
        pass

    def getIdentity(self):
        # Determine which sensor channel is active, prefer SENS1
        for ch in range(1, 5):
            try:
                if self.query_str(f'SENS{ch}:STAT?') == '1':
                    self.devNum = ch
                    print(f"Power Meter is connected on SENS{ch}")
                    break

            except Exception:
                continue

        if not self.devNum:
            print("Power Meter is NOT connected to SMB100A")
            self.devNum = 0
            return

        # Basic sensor setup
        ch = self.devNum
        model = self.query_str(f"SENS{ch}:TYPE?")
        print(f"Power Meter Model: '{model}'")

        sn = self.query_str(f"SENS{ch}:SNUM?")
        print(f"SN: '{sn}'")

        self.write_opc(f'SENS{ch}:UNIT DBM')
        self.write_opc(f'SENS{ch}:ZERO')
        self.write_opc(f'SENS{ch}:FILT:TYPE AUTO')

        outf = self.query_str(f'SENS{ch}:FREQ?')
        print(f'Frequency Set: {float(outf)/1e9} GHz')

        self.write_opc('INIT1:CONT OFF')

    def outputON(self):
        self.write_opc('OUTPut:STATe ON')

    def outputOFF(self):
        self.write_opc('OUTPut:STATe OFF')

    def freqModeCW(self):
        self.write_opc('SOURce:FREQuency:MODE CW')

    def powerLevel(self, pwrLevelTemp):
        self.write_opc(f'SOURce:POWer:LEVel:IMMediate:AMPLitude {pwrLevelTemp}')

    def CWFreq(self, freqTemp):
        self.write_opc(f'SOURce:FREQuency:FIXed {freqTemp}')

    def test(self):
        if not self.devNum:
            raise RuntimeError("Sensor channel not set")

        for f in freq:
            self.CWFreq(f)
            self.write_opc(f'SENS{self.devNum}:POWER:FREQ {f}')
            outp = self.query_float(f'READ{self.devNum}?')
            print(f'Freq = {f/1e9} GHz, Power Level = {outp} dBm')

    def getData(self):
        if not self.devNum:
            raise RuntimeError("Sensor channel not set")

        with open(PCFile, 'w', newline='') as logFile:
            logFile.write("Freq (GHz); Gain (dB)\n")

        for level in pwrLevel:
            self.powerLevel(level)
            with open(PCFile, 'a+') as logFile:
                logFile.write(f"Power Level (dBm);{level}\n")

            self.fileWrite()

    def fileWrite(self):
        if not self.devNum:
            raise RuntimeError("Sensor channel not set")

        outputPower: list[float] = []
        for f in freq:
            self.CWFreq(f)
            self.write_opc(f'SENS{self.devNum}:POWER:FREQ {f}')
            outp = self.query_float(f'READ{self.devNum}?')
            outputPower.append(outp)
            print(f'Freq = {f/1e9} GHz, Power Level = {outp} dBm')
            with open(PCFile, 'a+') as logFile:
                logFile.write(f"{f/1e9};{outp}\n")


if __name__ == "__main__":
    instrument = Instrument("172.16.3.13")
    try:
        instrument.open()
        instrument.getIdentity()
        instrument.comprep()
        instrument.freqModeCW()
        instrument.powerLevel(pwrLevel[0])
        instrument.outputON()
        instrument.getData()
        # instrument.test()
        instrument.outputOFF()

    finally:
        instrument.close()
