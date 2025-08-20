
import logging
from typing import Any

from Cerberus.plugins.equipment.mixins.parentDelegation import \
    SingleParentDelegationMixin
from Cerberus.plugins.equipment.powerMeters.basePowerMeters import \
    BasePowerMeter


class BaseNRPPowerMeter(SingleParentDelegationMixin, BasePowerMeter):
    """Facet style NRP power meter.

    This class no longer opens a separate VISA session. Instead it *delegates*
    all SCPI traffic to a required parent instrument (currently an SMB100A
    signal generator) that already owns the physical VISA connection.

    Initialisation contract:
      - Caller (dependency resolver) must provide the parent via
        ``initialise({'parent': parent_equipment})``.
      - If a parent is not supplied, initialisation fails fast.

    Benefits:
      * Maintains one physical connection to the SMB100A.
      * Keeps NRP sensors as distinct equipment plugins for requirement
        matching & test code clarity.
      * Enables future reuse with any instrument exposing the minimal SCPI
        protocol, without hard dependency on a concrete class.
    """

    # Declarative dependency (single parent)
    REQUIRED_PARENT: str | None = "SMB100A"

    def __init__(self, name: str):
        super().__init__(name)
        self.excluded = True  # Facet excluded from standalone dependency selection

    # --- Parent attachment ---------------------------------------------------------------------------------
    # attach_parent inherited from mixin

    # --- Lifecycle -----------------------------------------------------------------------------------------
    def initialise(self, init: Any | None = None) -> bool:  # type: ignore[override]
        # Expect dependency resolver to pass parent in init.
        if not self._ensure_parent(init):
            logging.error("%s: initialisation failed - required parent instrument not provided", self.name)
            return False
        # BaseCommsEquipment initialisation (via MRO chain: BasePowerMeter->BaseCommsEquipment)
        return BasePowerMeter.initialise(self)  # type: ignore[misc]

    def finalise(self) -> bool:  # type: ignore[override]
        # Parent owns the transport. Nothing to close here beyond normal finalise.
        return BasePowerMeter.finalise(self)

    # --- Basic VISA operations that are expected by the system
    def reset(self):
        pass

    # SCPI helpers now supplied by mixin
