import json
import logging
from typing import Any, Sequence

from numpy.polynomial import Chebyshev

from Cerberus.plugins.baseParameters import (BaseParameters, NumericParameter,
                                             StringParameter)
from Cerberus.plugins.equipment.baseCommsEquipment import BaseCommsEquipment


class CableParams(BaseParameters):
    def __init__(self):
        super().__init__("Cable")
        self.addParameter(StringParameter("Role", "TX", description="TX or RX"))
        self.addParameter(NumericParameter("MinFreq", 100.0, units="MHz"))
        self.addParameter(NumericParameter("MaxFreq", 3500.0, units="MHz"))
        self.addParameter(StringParameter("Coeefs", "{[]}", description="Coeffs for the Chebyshev cal"))


class CalibratedCable(BaseCommsEquipment):
    def __init__(self, name: str):
        super().__init__(name)
        self.addParameterGroup(CableParams())
        self._cheb: Chebyshev | None = None
        self._cal_meta: dict[str, Any] = {}

    def loadCalibrationFromJSON(self, calibration_json: str | None):
        if not calibration_json:
            logging.warning("No calibration JSON for cable %s", self.name)
            return

        try:
            data = json.loads(calibration_json)
            if data.get("method") == "chebyshev":
                coeffs: Sequence[float] = data["coeffs"]
                domain = tuple(data["domain"])
                self._cheb = Chebyshev(coeffs, domain=domain)
                self._cal_meta = data
            else:
                logging.error("Unsupported calibration method %r", data.get("method"))

        except Exception as e:
            logging.exception("Failed to parse calibration JSON: %s", e)

    def loss_at(self, freq_mhz: float) -> float:
        if self._cheb is None:
            return 0

        return float(self._cheb(freq_mhz))

    def __repr__(self):
        return f"Cable(name={self.name})"
