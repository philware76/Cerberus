"""BaseCommsShell: shared comms-capable shell abstraction.

Unifies direct vs delegated (single-parent) equipment communications:
 - Query / Write forwarding
 - Identity retrieval (direct VISA device or delegated parent VISA device)

Designed to be reusable for any shell that exposes low-level SCPI-like
operations over either a device implementing `CommsInterface` or a child
delegating through `SingleParentDelegationMixin`.
"""
from __future__ import annotations

from typing import Any, Tuple

from Cerberus.cmdShells.runCommandShell import RunCommandShell
from Cerberus.plugins.equipment.commsInterface import CommsInterface
from Cerberus.plugins.equipment.mixins.parentDelegation import \
    SingleParentDelegationMixin
from Cerberus.plugins.equipment.visaDevice import VISADevice


class _CommsAdapter:
    """Resolves an equipment's effective comms target (direct or delegated).

    This is intentionally lightweight; recreated after parent attach / detach.
    """

    def __init__(self, equip: Any):
        self._equip = equip
        self._target: Any | None
        self.delegated: bool = False
        self._target = self._resolve()

    def _resolve(self):
        equip = self._equip
        if isinstance(equip, CommsInterface):  # direct
            return equip

        if isinstance(equip, SingleParentDelegationMixin) and equip.has_parent():  # type: ignore[attr-defined]
            try:
                parent = equip._p()  # type: ignore[attr-defined]
                self.delegated = True
                return parent

            except Exception:
                return None

        return None

    def can_comms(self) -> bool:
        return self._target is not None

    def write(self, cmd: str) -> None:
        if not self.can_comms():
            raise RuntimeError("No communications target available")

        target = self._target
        assert target is not None, "_target unexpectedly None after can_comms()"

        # mypy/pylance: target now non-None
        target.write(cmd)  # type: ignore[attr-defined]

    def command(self, cmd: str):
        """Attempt an OPC-synchronised command if the target supports it.

        Falls back to plain write when no 'command' attribute exists.
        Returns whatever the underlying 'command' returns (often bool) or None.
        """
        if not self.can_comms():
            raise RuntimeError("No communications target available")

        target = self._target
        assert target is not None, "_target unexpectedly None after can_comms()"

        if hasattr(target, 'command'):
            return target.command(cmd)  # type: ignore[attr-defined]

        # fallback
        target.write(cmd)  # type: ignore[attr-defined]
        return None

    def query(self, cmd: str):
        if not self.can_comms():
            raise RuntimeError("No communications target available")

        target = self._target
        assert target is not None, "_target unexpectedly None after can_comms()"

        return target.query(cmd)  # type: ignore[attr-defined]

    def read(self, bytes):
        if not self.can_comms():
            raise RuntimeError("No communications target available")

        target = self._target
        assert target is not None, "_target unexpectedly None after can_comms()"

        return target.read(bytes)  # type: ignore[attr-defined]

    def identity(self) -> Tuple[str | None, bool]:
        tgt = self._target
        if isinstance(tgt, VISADevice):
            try:
                tgt.getIdentity()

            except Exception:
                pass

            ident = getattr(tgt, 'identity', None)
            return (str(ident) if ident else None, self.delegated)

        return (None, self.delegated)


class BaseCommsShell(RunCommandShell):
    """Base shell with common comms commands (query, write, identity).

    Subclasses should:
      * Call `_refresh_comms()` after any structural change (parent attach/detach).
      * Expose domain-specific commands separately.
    """

    def __init__(self, plugin, manager):
        super().__init__(plugin, manager)
        self._comms = _CommsAdapter(plugin)

    def _refresh_comms(self):
        self._comms = _CommsAdapter(self.plugin)

    def do_identity(self, arg):
        """Show identity (direct VISA or delegated parent VISA)."""
        ident, delegated = self._comms.identity()
        if ident:
            print(f"(Delegated) {ident}" if delegated else ident)
        else:
            print("Identity unavailable (not a VISA device or not attached).")
        return False

    def do_write(self, line):
        """write <cmd> : Plain SCPI write (no *OPC? wait)."""
        cmd = line.strip()
        if not cmd:
            print("Usage: write <SCPI>")
            return False
        if not self._comms.can_comms():
            print("No communications target (initialise or attach parent).")
            return False
        try:
            self._comms.write(cmd)
            print("Sent.")
        except Exception as ex:
            print(f"Write failed: {ex}")
        return False

    def do_cmd(self, line):
        """cmd <cmd> : SCPI command with *OPC? completion if supported.

        Uses device 'command()' method when available; falls back to plain write.
        Output:
          - Completed (OPC).  (command() returned True)
          - Command reported failure (OPC). (command() returned False)
          - Sent. (fallback path or non-bool return)
        """
        cmd = line.strip()
        if not cmd:
            print("Usage: cmd <SCPI>")
            return False

        if not self._comms.can_comms():
            print("No communications target (initialise or attach parent).")
            return False

        try:
            result = self._comms.command(cmd)
            if result is True:
                print("Completed (OPC).")

            elif result is False:
                print("Command reported failure (OPC).")

            else:
                print("Sent.")

        except Exception as ex:
            print(f"Command failed: {ex}")

        return False

    def do_query(self, line):
        """query <cmd> : Raw query; prints response if any."""
        cmd = line.strip()
        if not cmd:
            print("Usage: query <SCPI|command>")
            return False

        if not self._comms.can_comms():
            print("No communications target (initialise or attach parent).")
            return False

        try:
            resp = self._comms.query(cmd)
            if resp is not None:
                print(resp)

            else:
                print("(no response)" + (" (delegated)" if self._comms.delegated else ""))

        except Exception as ex:
            print(f"Query failed: {ex}")

        return False

    def do_read(self, line):
        """read <bytes> : Read number of <bytes> from device; prints response if any."""
        cmd = line.strip()
        if not cmd:
            print("Usage: read <bytes count>")
            return False

        """read : reads the comms port and prints response if any."""
        if not self._comms.can_comms():
            print("No communications target (initialise or attach parent).")
            return False

        try:
            resp = self._comms.read(int(line))
            if resp is not None:
                print(resp)

            else:
                print("(no response)" + (" (delegated)" if self._comms.delegated else ""))

        except Exception as ex:
            print(f"Read failed: {ex}")

        return False

    def do_drain(self, arg):
        """drain : Discard any pending unread VISA socket data (host & device buffers)."""
        # Access underlying target if it is a VISADevice
        target = getattr(self._comms, '_target', None)
        if isinstance(target, VISADevice):
            try:
                count = target.drain()
                print(f"Drained {count} bytes.")
            except Exception as ex:
                print(f"Drain failed: {ex}")
        else:
            print("Current equipment does not support drain().")
        return False
