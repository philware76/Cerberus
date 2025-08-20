import json
import logging
from typing import Any, Sequence

from numpy.polynomial import Chebyshev

from Cerberus.plugins.baseParameters import (BaseParameters, NumericParameter,
                                             StringParameter)
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment


class CableParams(BaseParameters):
    def __init__(self, role: str = "TX"):
        super().__init__("Cal Cable")
        self.addParameter(StringParameter("Role", role, description="TX or RX"))
        self.addParameter(StringParameter("Serial", "", description="Cable serial number"))
        self.addParameter(NumericParameter("Start", 100, minValue=100, maxValue=3500, units="MHz"))
        self.addParameter(NumericParameter("Stop", 3500, minValue=100, maxValue=3500, units="MHz"))
        self.addParameter(StringParameter("Coeffs", "{[]}", description="Coeffs for the Chebyshev cal"))


class BaseCalCable(BaseEquipment):
    def __init__(self, name: str):
        super().__init__(name + " Cal Cable")
        self.addParameterGroup(CableParams(name))
        self._cheb: Chebyshev | None = None
        self._cal_meta: dict[str, Any] = {}

    def loadCalibrationFromJSON(self, calibration_json: str | None):
        if not calibration_json:
            logging.warning("No calibration JSON for cable %s", self.name)
            return

        try:
            data = json.loads(calibration_json)
            if data.get("method") == "chebyshev":
                self.loadChebyshev(data)
            else:
                logging.error("Unsupported calibration method %r", data.get("method"))

        except Exception as e:
            logging.exception("Failed to parse calibration JSON: %s", e)

    def loadChebyshev(self, data):
        coeffs: Sequence[float] = data["coeffs"]
        domain = tuple(data["domain"])
        window = data["window"]

        self._cheb = Chebyshev(coeffs, domain=domain, window=window)
        self._cal_meta = data

        # Update parameter view if present
        try:
            self.updateParameters("Cable", {
                "MinFreq": float(domain[0]),
                "MaxFreq": float(domain[1]),
                "Coeffs": json.dumps(data)
            })

        except Exception:
            pass

    def loss_at(self, freq_mhz: float) -> float:
        if self._cheb is None:
            return 0

        return float(self._cheb(freq_mhz))

    def __repr__(self):
        return f"Cable(name={self.name})"
