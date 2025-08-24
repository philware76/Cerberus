
import logging
from typing import Any

from Cerberus.plugins.equipment.baseEquipment import Identity
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
        if not BasePowerMeter.initialise(self):  # type: ignore[misc]
            return False

        # Sanity-check: query connected sensor model and ensure plugin alignment
        try:
            ident = self.getIdentity()
            detected_model = (ident.model or "").strip().upper()
        except Exception:
            logging.exception("%s: failed to query NRP sensor identity", self.name)
            return False

        # If this concrete plugin expects a specific model, ensure it matches.
        expected_set = set()
        try:
            models = getattr(self, 'ACCEPTED_MODELS', None)
            if models:
                expected_set = {str(m).strip().upper() for m in models}
            else:
                m = getattr(self, 'EXPECTED_MODEL', None)
                if m:
                    expected_set = {str(m).strip().upper()}
        except Exception:
            expected_set = set()

        if expected_set and detected_model and detected_model not in expected_set:
            # Mismatch: let selection machinery try the other candidate.
            logging.warning("%s: detected sensor model %s not in accepted set %s", self.name, detected_model, sorted(expected_set))
            return False

        return True

    def finalise(self) -> bool:  # type: ignore[override]
        # Parent owns the transport. Nothing to close here beyond normal finalise.
        return BasePowerMeter.finalise(self)

    # --- Basic VISA operations that are expected by the system
    def reset(self):
        # No dedicated reset; rely on parent path if needed. Intentionally a no-op.
        return None

    def getIdentity(self) -> Identity:
        parent = self._p()  # SCPI parent from mixin
        model = parent.query("SENS1:TYPE?")
        serial = parent.query("SENS1:SNUM?")

        identity = Identity()
        identity.manufacturer = "R&S"
        identity.model = model
        identity.serial = serial
        identity.version = "SMB100A"

        # Cache if base class expects 'identity'
        try:
            self.identity = identity  # type: ignore[attr-defined]
        except Exception:
            pass

        return identity

    # SCPI helpers now supplied by mixin
