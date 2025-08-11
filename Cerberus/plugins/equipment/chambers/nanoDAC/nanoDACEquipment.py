import logging
from typing import Optional

from Cerberus.plugins.baseParameters import BaseParameters, NumericParameter
from Cerberus.plugins.basePlugin import hookimpl, singleton
from Cerberus.plugins.equipment.chambers.baseChamber import BaseChamber
from Cerberus.plugins.equipment.modbusClient import (ModbusError,
                                                     ModbusTCPClient)


@hookimpl
@singleton
def createEquipmentPlugin():
    return NanoDAC()

class NanoDAC(BaseChamber):
    def __init__(self):
        super().__init__("NanoDAC")
        # NOTE: These register addresses are placeholders until confirmed from manual.
        self._REG_SETPOINT = 0x0000      # Holding register: temperature setpoint (0.1C units?)
        self._REG_CURRENT_TEMP = 0x0001  # Input register: current temperature (0.1C units?)
        self._REG_STATUS = 0x0002        # Holding/Input register: status word
        self._client: Optional[ModbusTCPClient] = None

        # Additional Modbus parameters
        grp = BaseParameters("Modbus")
        grp.addParameter(NumericParameter("Unit ID", 1, units="", minValue=0, maxValue=247, description="Modbus Unit / Slave ID"))
        grp.addParameter(NumericParameter("Retries", 2, units="", minValue=0, maxValue=10, description="Retry attempts on transient errors"))
        self.addParameterGroup(grp)

    # --- Internal helpers ----------------------------------------------------------------------------------------
    def _get_modbus_client(self) -> ModbusTCPClient:
        if self._client:
            return self._client
        host = self.getParameterValue("Communication", "IP Address") or "127.0.0.1"
        port = int(self.getParameterValue("Communication", "Port") or 502)
        timeout_ms = int(self.getParameterValue("Communication", "Timeout") or 1000)
        unit_id = int(self.getParameterValue("Modbus", "Unit ID") or 1)
        timeout = max(0.05, timeout_ms / 1000.0)
        self._client = ModbusTCPClient(host, port=port, unit_id=unit_id, timeout=timeout)
        try:
            self._client.connect()
            logging.debug(f"NanoDAC connected Modbus TCP {host}:{port} unit {unit_id}")
        except Exception as ex:  # noqa: BLE001
            logging.error(f"NanoDAC Modbus connect failed {host}:{port} - {ex}")
            raise
        return self._client

    def _with_retries(self, func, *args, **kwargs):
        retries = int(self.getParameterValue("Modbus", "Retries") or 0)
        last_err = None
        for attempt in range(retries + 1):
            try:
                return func(*args, **kwargs)
            except (OSError, TimeoutError, ModbusError) as ex:  # noqa: PERF203
                last_err = ex
                logging.warning(f"Modbus op failed attempt {attempt+1}/{retries+1}: {ex}")
                if self._client:
                    self._client.close()
                self._client = None
        raise ModbusError(f"Operation failed after {retries+1} attempt(s): {last_err}")

    # --- Lifecycle overrides ------------------------------------------------------------------------------------
    def initialise(self, init=None) -> bool:  # type: ignore[override]
        try:
            self._get_modbus_client()
            return True
        except Exception:  # noqa: BLE001
            return False

    def finalise(self) -> bool:  # type: ignore[override]
        if self._client:
            self._client.close()
        self._client = None
        return super().finalise()

    # --- Chamber API overrides ----------------------------------------------------------------------------------
    def getTemperature(self) -> float:  # type: ignore[override]
        def op():
            client = self._get_modbus_client()
            regs = client.read_input_registers(self._REG_CURRENT_TEMP, 1)
            return regs[0]
        try:
            raw = self._with_retries(op)
            return raw / 10.0  # TODO: confirm scaling
        except ModbusError:
            return float('nan')

    def setTemperature(self, temperature: float):  # type: ignore[override]
        value = int(round(temperature * 10))
        def op():
            client = self._get_modbus_client()
            client.write_single_register(self._REG_SETPOINT, value)
        self._with_retries(op)
        super().setTemperature(temperature)

    # --- Extended NanoDAC helpers -------------------------------------------------------------------------------
    def readStatusWord(self) -> int:
        def op():
            client = self._get_modbus_client()
            regs = client.read_holding_registers(self._REG_STATUS, 1)
            return regs[0]
        return self._with_retries(op)