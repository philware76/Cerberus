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
        # Filter out excluded candidates with a single debug of who was skipped.
        pruned, excluded_names = self._filter_excluded_candidates(req_type, candidates)
        if not pruned:
            logger.error(f"All discovered candidates for requirement {req_type.__name__} are excluded (test: {test.name})")
            return None

        if excluded_names:
            logger.debug(f"Excluded candidates filtered for {req_type.__name__}: {excluded_names}")

        # Try cached reuse unless caller asked to refresh.
        if not force_refresh:
            reuse, skip_instance = self._reuse_cached_if_healthy(req_type)
        else:
            reuse, skip_instance = None, None

        if reuse is not None:
            return reuse

        # Fall back to first successfully initialised candidate (skipping a bad cached one if needed).
        filtered = [c for c in pruned if c is not skip_instance] if skip_instance is not None else pruned
        if skip_instance is not None and not filtered:
            logger.error(f"Only cached candidate for {req_type.__name__} failed health check and no alternative candidates are available")
            return None

        selected = self._initialise_first_online(req_type, filtered, test, skip_instance=skip_instance)
        if selected is None:
            return None

        self.cache.set(req_type, selected)

        return selected

    def _filter_excluded_candidates(self, req_type: type[BaseEquipment], candidates: list[BaseEquipment]) -> tuple[list[BaseEquipment], list[str]]:
        pruned = [c for c in candidates if not getattr(c, "excluded", False)]
        excluded_names = [c.name for c in candidates if getattr(c, "excluded", False)]

        return pruned, excluded_names

    def _reuse_cached_if_healthy(self, req_type: type[BaseEquipment]) -> tuple[BaseEquipment | None, BaseEquipment | None]:
        """Return a cached instance to reuse (if healthy) and/or one to skip.

        Parameters:
                req_type: The abstract equipment type being resolved.

        Returns:
                A tuple (reuse, skip_instance):
                    - reuse: The cached equipment instance to use immediately if it is
                        not excluded and passes the health check; otherwise None.
                    - skip_instance: If a cached instance exists but fails the health
                        check, this is that same instance so the caller can exclude it
                        from the current candidate iteration; otherwise None.

        Behaviour summary:
                - No cached entry → (None, None).
                - Cached is marked excluded → invalidate cache, return (None, None).
                - Cached passes _VISAHealthCheck → (cached, None).
                - Cached fails health check → invalidate cache, return (None, cached).
        """
        cached = self.cache.get(req_type)
        if cached is None:
            return None, None

        if getattr(cached, "excluded", False):
            logger.debug(f"Cached equipment {cached.name} for {req_type.__name__} is now marked excluded; invalidating cache entry")
            self.cache.invalidate(req_type)
            return None, None

        if self._VISAHealthCheck(cached):
            logger.debug(f"Reusing cached equipment {cached.name} for {req_type.__name__}")
            return cached, None

        logger.warning(f"Cached equipment {cached.name} for {req_type.__name__} failed health check; invalidating and selecting alternative")
        self.cache.invalidate(req_type)
        return None, cached

    def _initialise_first_online(self, req_type: type[BaseEquipment], candidates: list[BaseEquipment], test: BaseTest, *, skip_instance: BaseEquipment | None = None) -> BaseEquipment | None:
        # Iterate candidates, returning on first successful initialise. Uses early-continue
        # style and ensures only a single warning is emitted per failed candidate.
        total = len(candidates)
        for idx, equip in enumerate(candidates, start=1):
            if skip_instance is not None and equip is skip_instance:
                continue  # explicit skip of previously invalidated cached instance
            try:
                # Resolve & inject dependencies
                success, init_payload = self._prepare_dependencies(equip)
                if not success:
                    logger.warning(f"Skipping candidate {equip.name} due to dependency failure for {req_type.__name__}")  # noqa: E501
                    continue

                if equip.initialise(init_payload):
                    logger.debug(f"{equip.name} (#{idx}/{total}) initialised for requirement {req_type.__name__}")  # noqa: E501
                    return equip

                # Explicit failure (returned falsy)
                logger.warning(f"Candidate {equip.name} (#{idx}/{total}) failed to initialise for {req_type.__name__}")  # noqa: E501

            except Exception:
                # Log the exception once; don't emit a second generic failure message.
                logger.warning(f"Candidate {equip.name} (#{idx}/{total}) raised during initialise for {req_type.__name__}", exc_info=True)

        logger.error(
            f"All {total} candidates failed for requirement {req_type.__name__} in test {test.name}"  # noqa: E501
        )
        return None

    @staticmethod
    def _VISAHealthCheck(equip: BaseEquipment) -> bool:
        """Health check only for VISA Devices. Here we check if *IDN? still works"""
        if not isinstance(equip, VISADevice):
            return True  # Non‑comms equipment skipped from health validation.

        visaDevice = cast(VISADevice, equip)
        try:
            visaDevice.getIdentity()
        except EquipmentError:
            return False

        return True

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
