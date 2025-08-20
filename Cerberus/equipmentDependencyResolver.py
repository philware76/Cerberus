from typing import Any

from Cerberus.logConfig import getLogger
from Cerberus.manager import PluginService
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment

logger = getLogger("dependencyResolver")


class EquipmentDependencyResolver:
    """Resolves and prepares declared single-parent equipment dependencies before initialise.

    Uses the ``REQUIRED_PARENT`` string attribute on equipment (if present).
    Designed to be easily extended for multi-parent or graph resolution later.
    """

    def __init__(self, pluginService: PluginService):
        self.pluginService = pluginService

    def prepare_dependencies(self, equip: BaseEquipment) -> tuple[bool, dict[str, Any] | None]:
        """Ensure declared parents are present & initialised.

        Returns (success, init_payload) where:
          * success=False => dependency failure; caller should skip this candidate.
          * init_payload is a dict to pass into ``initialise`` (may be None).
        """
        parent_name = getattr(equip, "REQUIRED_PARENT", None)
        if not parent_name:
            return True, None  # no dependency declared

        parent = self.pluginService.findEquipment(parent_name)
        if parent is None:
            logger.error("%s: required parent '%s' not found", equip.name, parent_name)
            return False, None

        try:
            if not parent.initialise():
                logger.error("%s: failed to initialise required parent '%s'", equip.name, parent_name)
                return False, None
        except Exception:
            logger.error("%s: exception initialising required parent '%s'", equip.name, parent_name, exc_info=True)
            return False, None

        logger.debug("Injected %s into %s", parent.name, equip.name)
        return True, {"parent": parent}
