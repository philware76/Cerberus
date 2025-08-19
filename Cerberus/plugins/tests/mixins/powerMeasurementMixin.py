"""Reusable mixin for tests that can operate with either a dedicated
power meter or a spectrum analyser (which itself implements the
``BasePowerMeter`` interface).

Provides:
    - ``setup_power_path()``: Detect & configure the instrument.
    - ``take_power_measurement(freq)``: Unified API to acquire a power
      reading at a given frequency (in MHz) handling the appropriate
      settling and marker logic when a spectrum analyser is used.

Assumptions:
    - The test class using this mixin inherits from ``BaseTest`` and
      therefore implements ``getEquip`` and ``getGroupParameters``.
    - A group parameter providing at least ``MinSamples`` may exist when
      spectrum analyser settling is required (falls back to 5 if absent).

Intended to be mixed into concrete test classes BEFORE ``BaseTest`` so
that any potential method name clashes are resolved in favour of test
customisations.
"""
from __future__ import annotations

from typing import Any, Protocol, cast, runtime_checkable

from Cerberus.common import dwell
from Cerberus.plugins.common import getSettledReading
from Cerberus.plugins.equipment.powerMeters.basePowerMeters import \
    BasePowerMeter
from Cerberus.plugins.equipment.spectrumAnalysers.baseSpecAnalyser import \
    BaseSpecAnalyser
from Cerberus.plugins.equipment.visaDevice import VISADevice


@runtime_checkable
class _HasLogger(Protocol):  # pragma: no cover - convenience protocol
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


class PowerMeasurementMixin:
    """Mixin encapsulating dual power meter / spectrum analyser logic."""

    powerMeter: BasePowerMeter

    # Public API ---------------------------------------------------------------------------------
    def setup_power_path(self) -> None:
        """Discover and configure the power measuring path.

        If the discovered equipment is a spectrum analyser additional
        analyser specific configuration is applied.
        """
        self.powerMeter = self.getEquip(BasePowerMeter)  # type: ignore[attr-defined]
        if isinstance(self.powerMeter, BaseSpecAnalyser):
            self._config_spec_analyser(self.powerMeter)
        else:
            self._config_power_meter(self.powerMeter)

    def take_power_measurement(self, freq_mhz: float, *, min_samples: int | None = None) -> float:
        """Acquire a power measurement at ``freq_mhz``.

        For a spectrum analyser we centre the span on the frequency, peak
        the marker, then obtain a settled reading (averaging until stable).
        For a plain power meter we simply tune and read.
        """
        if isinstance(self.powerMeter, BaseSpecAnalyser):
            return self._take_spec_marker_measurement(freq_mhz, min_samples=min_samples)
        return self._take_power_meter_reading(freq_mhz)

    # Internal helpers ----------------------------------------------------------------------------
    def _config_spec_analyser(self, sa: BaseSpecAnalyser) -> None:
        cast(VISADevice, sa).reset()
        sa.setRefInput("INT")
        sa.setSpan(10)
        sa.setBWS("NUTT")
        sa.setRBW(10)
        sa.setVBW(10)
        sa.setRefLevel(-10)

    def _config_power_meter(self, pm: BasePowerMeter) -> None:
        visa = cast(VISADevice, pm)
        visa.reset()
        visa.command("INITiate:CONTinuous ON")

    def _take_power_meter_reading(self, freq_mhz: float) -> float:
        self.powerMeter.setFrequency(freq_mhz)
        dwell(0.5)
        return self.powerMeter.getPowerReading()

    def _take_spec_marker_measurement(self, freq_mhz: float, *, min_samples: int | None = None) -> float:
        sa = cast(BaseSpecAnalyser, self.powerMeter)
        sa.setCentre(freq_mhz)
        dwell(0.5)
        sa.setMarkerPeak()
        dwell(0.5)

        if min_samples is None:
            # Attempt to get from parameters (silent if absent)
            try:
                gp = self.getGroupParameters("Calibration")  # type: ignore[attr-defined]
                min_samples = int(gp.get("MinSamples", 5))
            except Exception:
                min_samples = 5
        min_samples = max(1, int(min_samples))

        marker_pwr = getSettledReading(sa.getMarkerPower, min_samples)
        return round(marker_pwr, 2)
        marker_pwr = getSettledReading(sa.getMarkerPower, min_samples)
        return round(marker_pwr, 2)
