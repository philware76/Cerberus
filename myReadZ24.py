import pathlib
import time

import numpy as np

from Cerberus.plugins.equipment.visaDevice import VISADevice

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
    """SMB100A + delegated NRP sensor control using Cerberus VISADevice.

    This adapts the original standalone example to use the existing Cerberus
    VISA abstraction so behaviour is comparable to the framework environment.
    Only a lightweight subset of the original helper methods is retained.
    """

    def __init__(self, ip_address: str, timeout_ms: int = 10000, port: int = 5025):
        self.ip_address = ip_address
        self.timeout_ms = timeout_ms
        self.devNum: int | None = None
        # Re‑use Cerberus VISADevice (socket based)
        self.visa = VISADevice(port=port, ipAddress=ip_address, timeout=timeout_ms)

    def open(self):
        inst = self.visa.open()
        if inst is None:
            raise RuntimeError("Failed to open VISA device")

        # Diagnostics
        print(f"Timeout: {inst.timeout} ms")
        print(f"Read termination: {repr(inst.read_termination)}")
        print(f"Write termination: {repr(inst.write_termination)}")

        idn = self.query_str("*IDN?")
        print(f"*IDN? => {idn}")
        self.write("*CLS")
        self.write_opc("*RST")

    def close(self):
        try:
            # Graceful power drop if possible
            self.write_opc('SOURce:POWer:LEVel:IMMediate:AMPLitude -100')
        except Exception:
            pass
        self.visa.close()

    # ---------- SCPI convenience (wrappers) ----------
    def write(self, cmd: str):
        self.visa.write(cmd)

    def query_str(self, cmd: str) -> str:
        return self.visa.query(cmd).strip()

    def query_float(self, cmd: str) -> float:
        return float(self.query_str(cmd))

    def write_opc(self, cmd: str):
        # Use VISADevice.command which writes then waits for *OPC? internally
        ok = self.visa.command(cmd)
        if not ok:
            raise RuntimeError(f"OPC wait failed for command: {cmd}")

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
