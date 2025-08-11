"""Lightweight Modbus/TCP helper for equipment plugins.

This is intentionally minimal (no external deps) and covers the core
function codes we expect to need initially:
  - 0x03 Read Holding Registers
  - 0x04 Read Input Registers
  - 0x06 Write Single Register
  - 0x10 Write Multiple Registers

It is NOT a full Modbus stack (no coils/discretes for now, no fragmentation,
no advanced diagnostics). Extend as needed.

Design goals:
  - Simple, dependency-free
  - Safe: timeouts, graceful error handling, clear exceptions
  - Reusable across multiple equipment plugins (e.g., chambers, PSUs, etc.)

All register addresses used by concrete equipment classes MUST be defined
in those classes (avoid scattering magic numbers inside this helper).
"""
from __future__ import annotations

import socket
import struct
import threading
from typing import List, Sequence


class ModbusError(RuntimeError):
    pass


class ModbusTCPClient:
    def __init__(self, host: str, port: int = 502, unit_id: int = 1, timeout: float = 1.0):
        self.host = host
        self.port = port
        self.unit_id = unit_id & 0xFF
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()
        self._transaction_id = 0

    # --- Connection lifecycle ------------------------------------------------------------------------------------
    def connect(self):
        if self._sock:
            return
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock.settimeout(self.timeout)

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # --- Core helpers --------------------------------------------------------------------------------------------
    def _next_tid(self) -> int:
        self._transaction_id = (self._transaction_id + 1) & 0xFFFF
        return self._transaction_id

    def _send_pdu(self, function_code: int, payload: bytes) -> bytes:
        if not self._sock:
            raise ModbusError("Socket not connected")
        with self._lock:
            tid = self._next_tid()
            length = 1 + len(payload) + 1  # unit id + function + payload
            # MBAP: Transaction ID (2) + Protocol ID (2) + Length (2) + Unit ID (1)
            header = struct.pack(
                ">HHHB", tid, 0x0000, length, self.unit_id
            )
            adu = header + struct.pack("B", function_code) + payload
            self._sock.sendall(adu)
            # Read MBAP header (7 bytes)
            mbap = self._recv_exact(7)
            r_tid, proto, r_len, r_uid = struct.unpack(
                ">HHHB", mbap
            )
            if r_tid != tid:
                raise ModbusError(f"Transaction ID mismatch (sent {tid}, got {r_tid})")
            if proto != 0:
                raise ModbusError("Unsupported protocol identifier")
            if r_uid != self.unit_id:
                raise ModbusError("Unit ID mismatch in response")
            # Remaining: length-1 bytes (function + data/exception)
            pdu = self._recv_exact(r_len - 1)
            if not pdu:
                raise ModbusError("Empty PDU in response")
            resp_fc = pdu[0]
            if resp_fc & 0x80:
                # Exception: next byte is exception code
                code = pdu[1] if len(pdu) > 1 else 0x00
                raise ModbusError(f"Modbus exception (fc=0x{resp_fc:02X}, code=0x{code:02X})")
            if resp_fc != function_code:
                raise ModbusError(
                    f"Unexpected function code in response (0x{resp_fc:02X} != 0x{function_code:02X})"
                )
            return pdu[1:]  # strip function code

    def _recv_exact(self, size: int) -> bytes:
        if not self._sock:
            raise ModbusError("Socket not connected")
        buf = bytearray()
        while len(buf) < size:
            chunk = self._sock.recv(size - len(buf))
            if not chunk:
                raise ModbusError("Connection closed while receiving")
            buf.extend(chunk)
        return bytes(buf)

    # --- Public Modbus operations --------------------------------------------------------------------------------
    def read_holding_registers(self, address: int, count: int) -> List[int]:
        if count < 1 or count > 125:
            raise ValueError("count must be 1..125")
        payload = struct.pack(">HH", address, count)
        data = self._send_pdu(0x03, payload)
        if not data:
            raise ModbusError("No data in read_holding response")
        byte_count = data[0]
        reg_bytes = data[1:]
        if byte_count != len(reg_bytes) or byte_count != count * 2:
            raise ModbusError("Byte count mismatch in holding register response")
        return [struct.unpack(">H", reg_bytes[i:i+2])[0] for i in range(0, byte_count, 2)]

    def read_input_registers(self, address: int, count: int) -> List[int]:
        if count < 1 or count > 125:
            raise ValueError("count must be 1..125")
        payload = struct.pack(">HH", address, count)
        data = self._send_pdu(0x04, payload)
        if not data:
            raise ModbusError("No data in read_input response")
        byte_count = data[0]
        reg_bytes = data[1:]
        if byte_count != len(reg_bytes) or byte_count != count * 2:
            raise ModbusError("Byte count mismatch in input register response")
        return [struct.unpack(">H", reg_bytes[i:i+2])[0] for i in range(0, byte_count, 2)]

    def write_single_register(self, address: int, value: int) -> None:
        if not (0 <= value <= 0xFFFF):
            raise ValueError("value must fit in 16 bits")
        payload = struct.pack(">HH", address, value)
        echo = self._send_pdu(0x06, payload)
        if len(echo) != 4:
            raise ModbusError("Unexpected length in single register write echo")
        r_addr, r_val = struct.unpack(">HH", echo)
        if r_addr != address or r_val != value:
            raise ModbusError("Write single register echo mismatch")

    def write_multiple_registers(self, address: int, values: Sequence[int]) -> None:
        if not values:
            raise ValueError("values must be non-empty")
        if len(values) > 123:
            raise ValueError("Too many registers (max 123)")
        for v in values:
            if not (0 <= v <= 0xFFFF):
                raise ValueError("register values must be 0..65535")
        count = len(values)
        reg_bytes = b"".join(struct.pack(">H", v) for v in values)
        payload = struct.pack(">HHB", address, count, count * 2) + reg_bytes
        echo = self._send_pdu(0x10, payload)
        if len(echo) != 4:
            raise ModbusError("Unexpected length in multiple register write echo")
        r_addr, r_count = struct.unpack(">HH", echo)
        if r_addr != address or r_count != count:
            raise ModbusError("Write multiple register echo mismatch")
