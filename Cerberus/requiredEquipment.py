from __future__ import annotations

from typing import Any, Dict, Optional, Type, cast

from Cerberus.exceptions import EquipmentError
from Cerberus.logConfig import getLogger
from Cerberus.manager import PluginService
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment
from Cerberus.plugins.equipment.visaDevice import VISADevice
from Cerberus.plugins.tests.baseTest import BaseTest

logger = getLogger("requiredEquipment")


class RequirementCache:
    """Caches resolved equipment instances per abstract requirement type.

    The cache key is the abstract required equipment type (a subclass of
    BaseEquipment) and the value is the concrete plugin instance that was
    successfully initialised for that requirement during a previous test run.
    """

    def __init__(self):
        self._cache: Dict[Type[BaseEquipment], BaseEquipment] = {}

    # --- Basic operations -------------------------------------------------------------------------------------
    def get(self, req_type: Type[BaseEquipment]) -> Optional[BaseEquipment]:
        return self._cache.get(req_type)

    def set(self, req_type: Type[BaseEquipment], instance: BaseEquipment) -> None:
        self._cache[req_type] = instance

    def invalidate(self, req_type: Type[BaseEquipment]) -> None:
        self._cache.pop(req_type, None)

    def clear(self) -> None:
        self._cache.clear()


class RequiredEquipment:
    """Resolves and injects required equipment for a test, reusing cached selections.

    Features:
      * Caches previously-initialised equipment by required abstract type.
      * Performs a light "health" check on cached equipment before reuse.
      * Invalidates and falls back to candidate search if health check fails.
    """

    def __init__(self, pluginService: PluginService, cache: RequirementCache | None = None):
        self.pluginService = pluginService
        self.cache = cache or RequirementCache()

    # --- Public API -------------------------------------------------------------------------------------------
    def prepare(self, test: BaseTest, force_refresh: bool = False) -> bool:
        """Resolve equipment for test, reusing cache and showing a clear top-level flow.

        If ``force_refresh`` is True the cache is ignored for this call (but still updated with fresh selections).
        """
        reqs = self.pluginService.getRequirements(test)
        if reqs.missing:
            self._log_missing_requirements(test, reqs.missing)
            return False

        equip_map: Dict[Type[BaseEquipment], BaseEquipment] = {}
        for req_type, candidates in reqs.candidates.items():
            chosen = self._select_equipment_for_requirement(req_type, candidates, test, force_refresh)
            if chosen is None:
                return False

            equip_map[req_type] = chosen

        test.provideEquip(equip_map)
        return True

    def flush_cache(self) -> None:
        """Completely clear the requirement cache (manual invalidation)."""
        self.cache.clear()
        logger.debug("Requirement cache cleared")

    # --- Internal helpers -------------------------------------------------------------------------------------
    @staticmethod
    def _log_missing_requirements(test: BaseTest, missing: list[type[BaseEquipment]]) -> None:
        missing_names = [t.__name__ for t in missing]
        logger.error(f"Missing required equipment for test: {test.name}. Missing: {missing_names}")  # noqa: E501

    def _select_equipment_for_requirement(self, req_type: type[BaseEquipment], candidates: list[BaseEquipment], test: BaseTest, force_refresh: bool) -> BaseEquipment | None:
        """Select and initialize equipment for a requirement, with clear step-by-step flow."""

        # Step 1: Filter excluded candidates
        viable_candidates, excluded_names = self._filter_excluded_candidates(req_type, candidates)
        if not viable_candidates:
            logger.error(f"All discovered candidates for requirement {req_type.__name__} are excluded (test: {test.name})")
            return None

        if excluded_names:
            logger.debug(f"Excluded candidates filtered for {req_type.__name__}: {excluded_names}")

        # Step 2: Try cache reuse (unless force refresh requested)
        if not force_refresh:
            cached_result = self._try_cache_reuse(req_type, viable_candidates)
            if cached_result is not None:
                return cached_result

        # Step 3: Initialize first working candidate
        selected = self._initialize_first_working_candidate(req_type, viable_candidates, test)
        if selected is not None:
            self.cache.set(req_type, selected)

        return selected

    def _try_cache_reuse(self, req_type: type[BaseEquipment], viable_candidates: list[BaseEquipment]) -> BaseEquipment | None:
        """Try to reuse cached equipment if it's still healthy and not excluded."""
        cached = self.cache.get(req_type)
        if cached is None:
            return None

        # Check if cached equipment is now excluded
        if getattr(cached, "excluded", False):
            logger.debug(f"Cached equipment {cached.name} for {req_type.__name__} is now marked excluded; invalidating cache entry")
            self.cache.invalidate(req_type)
            return None

        # Health check cached equipment
        if self._VISAHealthCheck(cached):
            logger.debug(f"Reusing cached equipment {cached.name} for {req_type.__name__}")
            return cached

        # Cache failed health check - invalidate and continue with fresh search
        logger.warning(f"Cached equipment {cached.name} for {req_type.__name__} failed health check; invalidating and selecting alternative")
        self.cache.invalidate(req_type)
        return None

    def _initialize_first_working_candidate(self, req_type: type[BaseEquipment], candidates: list[BaseEquipment], test: BaseTest) -> BaseEquipment | None:
        """Try to initialize candidates until one works, returning the first successful one."""
        total = len(candidates)
        for idx, equip in enumerate(candidates, start=1):
            try:
                # Resolve & inject dependencies
                success, init_payload = self._prepare_dependencies(equip)
                if not success:
                    logger.warning(f"Skipping candidate {equip.name} due to dependency failure for {req_type.__name__}")
                    continue

                if equip.initialise(init_payload):
                    logger.debug(f"{equip.name} (#{idx}/{total}) initialised for requirement {req_type.__name__}")
                    return equip

                # Explicit failure (returned falsy)
                logger.warning(f"Candidate {equip.name} (#{idx}/{total}) failed to initialise for {req_type.__name__}")

            except Exception:
                # Log the exception once; don't emit a second generic failure message.
                logger.warning(f"Candidate {equip.name} (#{idx}/{total}) raised during initialise for {req_type.__name__}", exc_info=True)

        logger.error(f"All {total} candidates failed for requirement {req_type.__name__} in test {test.name}")
        return None

    def _filter_excluded_candidates(self, req_type: type[BaseEquipment], candidates: list[BaseEquipment]) -> tuple[list[BaseEquipment], list[str]]:
        pruned = [c for c in candidates if not getattr(c, "excluded", False)]
        excluded_names = [c.name for c in candidates if getattr(c, "excluded", False)]

        return pruned, excluded_names

    @staticmethod
    def _VISAHealthCheck(equip: BaseEquipment) -> bool:
        """Simple health check for VISA Devices using *IDN? query.

        Returns True for non-VISA equipment (no check needed).
        Returns True if VISA device responds to getIdentity().
        Returns False if VISA device fails to respond.
        """
        if not isinstance(equip, VISADevice):
            return True  # Non-VISA equipment always considered healthy

        visaDevice = cast(VISADevice, equip)
        try:
            identity = visaDevice.getIdentity()
            # Consider device healthy if we get any identity response
            return identity is not None
        except (EquipmentError, Exception) as e:
            logger.debug(f"VISA health check failed for {equip.name}: {e}")
            return False

    def _prepare_dependencies(self, equip: BaseEquipment) -> tuple[bool, dict[str, Any] | None]:
        parent_name = getattr(equip, "REQUIRED_PARENT", None)
        if not parent_name:
            return True, None

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
