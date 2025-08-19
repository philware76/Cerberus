from __future__ import annotations

from typing import Dict, Optional, Type

from Cerberus.equipmentDependencyResolver import EquipmentDependencyResolver
from Cerberus.logConfig import getLogger
from Cerberus.manager import PluginService
from Cerberus.plugins.equipment.baseEquipment import BaseEquipment, Identity
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
        self._depResolver = EquipmentDependencyResolver(pluginService)

    # --- Public API -------------------------------------------------------------------------------------------
    def prepare(self, test: BaseTest, force_refresh: bool = False) -> bool:
        """Resolve equipment for test, reusing cached matches when available.

        If ``force_refresh`` is True the cache is ignored for this call (but
        still updated with fresh selections).
        """
        reqs = self.pluginService.getRequirements(test)

        if reqs.missing:
            self._log_missing_requirements(test, reqs.missing)
            return False

        equip_map: Dict[Type[BaseEquipment], BaseEquipment] = {}

        for req_type, candidates in reqs.candidates.items():
            selected: BaseEquipment | None = None
            skip_instance: BaseEquipment | None = None

            if not force_refresh:
                cached = self.cache.get(req_type)
                if cached is not None:
                    if self._health_check(cached):
                        logger.debug(f"Reusing cached equipment {cached.name} for {req_type.__name__}")
                        selected = cached
                    else:
                        logger.warning(
                            f"Cached equipment {cached.name} for {req_type.__name__} failed health check; invalidating and selecting alternative"
                        )
                        self.cache.invalidate(req_type)
                        skip_instance = cached  # Do not reconsider this instance in this selection cycle

            if selected is None:
                # Filter out skip_instance for this attempt only
                if skip_instance is not None:
                    filtered_candidates = [c for c in candidates if c is not skip_instance]
                else:
                    filtered_candidates = candidates

                if skip_instance is not None and not filtered_candidates:
                    logger.error(
                        f"Only cached candidate for {req_type.__name__} failed health check and no alternative candidates are available"
                    )
                    return False

                selected = self._initialise_first_online(req_type, filtered_candidates, test, skip_instance=skip_instance)
                if selected is None:
                    # Failure already logged; abort entire preparation.
                    return False
                self.cache.set(req_type, selected)

            equip_map[req_type] = selected

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
        logger.error(
            f"Missing required equipment for test: {test.name}. Missing: {missing_names}"  # noqa: E501
        )

    def _initialise_first_online(self, req_type: type[BaseEquipment], candidates: list[BaseEquipment], test: BaseTest, *, skip_instance: BaseEquipment | None = None) -> BaseEquipment | None:
        # Iterate candidates, returning on first successful initialise. Uses early-continue
        # style and ensures only a single warning is emitted per failed candidate.
        total = len(candidates)
        for idx, equip in enumerate(candidates, start=1):
            if skip_instance is not None and equip is skip_instance:
                continue  # explicit skip of previously invalidated cached instance
            try:
                # Resolve & inject dependencies
                success, init_payload = self._depResolver.prepare_dependencies(equip)
                if not success:
                    logger.warning(
                        f"Skipping candidate {equip.name} due to dependency failure for {req_type.__name__}"  # noqa: E501
                    )
                    continue
                if equip.initialise(init_payload):
                    logger.debug(
                        f"{equip.name} (#{idx}/{total}) initialised for requirement {req_type.__name__}"  # noqa: E501
                    )
                    return equip
                # Explicit failure (returned falsy)
                logger.warning(
                    f"Candidate {equip.name} (#{idx}/{total}) failed to initialise for {req_type.__name__}"  # noqa: E501
                )
            except Exception:
                # Log the exception once; don't emit a second generic failure message.
                logger.warning(
                    f"Candidate {equip.name} (#{idx}/{total}) raised during initialise for {req_type.__name__}",
                    exc_info=True,
                )

        logger.error(
            f"All {total} candidates failed for requirement {req_type.__name__} in test {test.name}"  # noqa: E501
        )
        return None

    @staticmethod
    def _health_check(equip: BaseEquipment) -> bool:
        """Perform a lightweight health check on a cached equipment instance.

        Strategy (best-effort):
          1. If it has a callable ``identity`` attribute, call it and ensure we
             get a plausible Identity object (model not 'Unknown'). This may
             issue an *IDN? query for VISA-based instruments.
          2. Else if it has an ``identity`` attribute (object), inspect for a
             non-'Unknown' model.
          3. Fallback: assume healthy (return True) – avoids false negatives
             for equipment without identity support.
        Any exception => unhealthy.
        """
        try:
            ident_attr = getattr(equip, "identity", None)
            if callable(ident_attr):  # Method style
                ident = ident_attr()
                if isinstance(ident, Identity):
                    model = getattr(ident, "model", "")
                    return bool(model and model != "Unknown")

                return ident is not None

            if ident_attr is not None:  # Attribute style
                model = getattr(ident_attr, "model", None)
                if model is not None:
                    return model != "Unknown"

            # No identity information – treat as healthy.
            return True

        except Exception:
            logger.debug("Health check exception", exc_info=True)
            return False
