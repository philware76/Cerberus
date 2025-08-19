
import logging
from typing import Any, Optional, Protocol, runtime_checkable

from Cerberus.plugins.equipment.baseEquipment import BaseCommsEquipment
from Cerberus.plugins.equipment.powerMeters.basePowerMeters import \
    BasePowerMeter


@runtime_checkable
class _SCPIParent(Protocol):
    """Structural protocol describing the minimal SCPI surface required.

    Any parent instrument (e.g. an initialised "SMB100A") that supplies these
    methods can act as the transport provider for an NRP sensor facet.
    """

    def write(self, command: str) -> None: ...  # noqa: D401,E701 (structural only)
    def query(self, command: str) -> str: ...
    def command(self, command: str) -> bool: ...
    def operationComplete(self) -> bool: ...
    @property
    def name(self) -> str: ...


class BaseNRPPowerMeter(BasePowerMeter):
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

    # Declarative dependency (resolved externally by RequiredEquipment logic)
    REQUIRED_PARENTS: list[str] = ["SMB100A"]

    def __init__(self, name: str):
        super().__init__(name)
        self._parent: Optional[_SCPIParent] = None

    # --- Parent attachment ---------------------------------------------------------------------------------
    def attach_parent(self, parent: _SCPIParent) -> None:
        if not isinstance(parent, _SCPIParent):  # runtime structural guard (optional)
            raise TypeError("Parent does not satisfy SCPI parent protocol")
        self._parent = parent
        logging.debug("%s attached to parent %s", self.name, parent.name)

    # --- Lifecycle -----------------------------------------------------------------------------------------
    def initialise(self, init: Any | None = None) -> bool:  # type: ignore[override]
        # Expect dependency resolver to pass parent in init.
        if init and isinstance(init, dict) and 'parent' in init and self._parent is None:
            self.attach_parent(init['parent'])  # type: ignore[arg-type]

        if self._parent is None:
            logging.error("%s: initialisation failed - required parent instrument not provided", self.name)
            return False

        return BaseCommsEquipment.initialise(self)

    def finalise(self) -> bool:  # type: ignore[override]
        # Parent owns the transport. Nothing to close here.
        return BasePowerMeter.finalise(self)

    # --- Delegated SCPI helpers ---------------------------------------------------------------------------
    def _p(self) -> _SCPIParent:
        if self._parent is None:
            raise RuntimeError("SCPI parent not attached")
        return self._parent

    def write(self, command: str) -> None:  # noqa: D401
        self._p().write(command)

    def query(self, command: str) -> str:  # noqa: D401
        return self._p().query(command)

    def command(self, command: str) -> bool:  # noqa: D401
        return self._p().command(command)

    def operationComplete(self) -> bool:  # noqa: D401
        return self._p().operationComplete()
