"""Reusable single-parent SCPI delegation mixin.

This mixin lets an equipment *facet* delegate all SCPI/communication calls to
an already-initialised parent instrument that owns the physical connection.

Features:
  * Declarative dependency via ``REQUIRED_PARENT: str | None`` (single parent).
  * Manual attachment through ``attach_parent``.
  * Optional auto-resolution during ``initialise`` via the global ``PluginService``.
  * Delegated helper methods: ``write``, ``query``, ``command``, ``operationComplete``.

Adoption steps for an equipment class:
  1. Inherit from ``SingleParentDelegationMixin`` *before* the concrete base
     equipment class so its initialise hook can be called easily.
  2. Set ``REQUIRED_PARENT = "ParentEquipName"`` (or leave ``None`` if dynamic).
  3. In ``initialise`` call ``self._ensure_parent(init)`` before other work.

There is no legacy multi-parent list; the canonical declaration is a single
``REQUIRED_PARENT" string (or None if no parent is required).
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class _SCPIParent(Protocol):  # Minimal structural surface expected from parent
    def write(self, command: str) -> None: ...  # noqa: D401,E701
    def query(self, command: str) -> str: ...
    def read(self, bytes: int) -> str: ...
    def command(self, command: str) -> bool: ...
    def operationComplete(self) -> bool: ...

    @property
    def name(self) -> str: ...  # noqa: D401


class SingleParentDelegationMixin:
    """Mixin implementing single-parent SCPI delegation.

    Attributes:
        REQUIRED_PARENT: Optional[str] name of the required parent instrument.
    """

    REQUIRED_PARENT: Optional[str] = None  # Override in subclasses

    def __init__(self, *args, **kwargs):  # type: ignore[override]
        super().__init__(*args, **kwargs)  # type: ignore[misc]
        self._parent: Optional[_SCPIParent] = None

    # ----------------------------------------------------------------------------------
    def attach_parent(self, parent: _SCPIParent) -> None:
        if not isinstance(parent, _SCPIParent):  # runtime structural guard
            raise TypeError("Parent does not satisfy SCPI parent protocol")
        self._parent = parent
        logging.debug("%s attached to parent %s", getattr(self, 'name', '<unnamed>'), parent.name)

    def detach_parent(self) -> None:
        if self._parent is not None:
            logging.debug("%s detached from parent %s", getattr(self, 'name', '<unnamed>'), self._parent.name)

        self._parent = None

    def has_parent(self) -> bool:
        return self._parent is not None

    def parent_name_required(self) -> Optional[str]:
        return self.REQUIRED_PARENT

    # ----------------------------------------------------------------------------------
    def _ensure_parent(self, init: Any | None = None) -> bool:
        """Internal helper: attempt to satisfy parent requirement.

        Order of resolution:
          1. If already attached -> OK.
          2. If ``init`` supplies 'parent' -> attach.
          3. If ``REQUIRED_PARENT`` declared -> look it up via PluginService singleton and attach.
        Returns True on success (or no requirement), False if required parent missing / failed.
        """
        if self._parent is not None:
            return True

        # 2. Provided via init payload
        if init and isinstance(init, dict) and 'parent' in init:
            try:
                self.attach_parent(init['parent'])  # type: ignore[arg-type]
                return True

            except Exception:
                logging.exception("Failed to attach provided parent")
                return False

        # 3. Declarative lookup
        if self.REQUIRED_PARENT:
            try:
                from Cerberus.pluginService import \
                    PluginService  # local import to avoid cycles
                ps = PluginService.instance()

                if ps is None:
                    logging.error("PluginService instance unavailable for parent resolution")
                    return False

                parent = ps.findEquipment(self.REQUIRED_PARENT)
                if parent is None:
                    logging.error("%s: required parent '%s' not found", getattr(self, 'name', '<unnamed>'), self.REQUIRED_PARENT)
                    return False

                # Ensure parent initialised before delegation
                try:
                    if hasattr(parent, 'initialise'):
                        parent.initialise()

                except Exception:
                    logging.exception("%s: exception initialising parent %s", getattr(self, 'name', '<unnamed>'), parent.name)
                    return False

                self.attach_parent(parent)  # type: ignore[arg-type]
                return True

            except Exception:
                logging.exception("Unexpected error resolving parent")
                return False

        # No requirement
        return True

    # ----------------------------------------------------------------------------------
    def _p(self) -> _SCPIParent:
        if self._parent is None:
            raise RuntimeError("SCPI parent not attached")

        return self._parent

    # Delegated helpers (expected by rest of system if present) -----------------------
    def write(self, command: str) -> None:  # type: ignore[override]
        self._p().write(command)

    def read(self, bytes: int) -> str:  # type: ignore[override]
        return self._p().read(bytes)

    def query(self, command: str) -> str:  # type: ignore[override]
        return self._p().query(command)

    def command(self, command: str) -> bool:  # type: ignore[override]
        return self._p().command(command)

    def operationComplete(self) -> bool:  # type: ignore[override]
        return self._p().operationComplete()

    # No legacy list API retained; if future expansion needed, extend here.
