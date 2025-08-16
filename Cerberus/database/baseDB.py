from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from Cerberus.plugins.baseParameters import BaseParameter
from Cerberus.plugins.basePlugin import BasePlugin


class BaseDB(ABC):
    """
    Abstract interface for generic plugin parameter persistence.
    Implementations:
      - MySQL: GenericDB
      - File / in‑memory: (future) FileGenericDB
    """

    def __init__(self, station_id: str):
        self.station_id = station_id

    # ---- Save single / bulk -------------------------------------------------
    @abstractmethod
    def save_parameter(self,
                       plugin_type: str,
                       plugin_name: str,
                       group_name: str,
                       param: BaseParameter) -> None: ...

    @abstractmethod
    def save_plugin(self, plugin_type: str, plugin: BasePlugin) -> None: ...

    @abstractmethod
    def save_many(self, plugin_type: str, plugins: Iterable[BasePlugin]) -> None: ...

    # Convenience bulk helpers
    @abstractmethod
    def save_equipment(self, equipment_plugins: Iterable[BasePlugin]) -> None: ...

    @abstractmethod
    def save_tests(self, test_plugins: Iterable[BasePlugin]) -> None: ...

    @abstractmethod
    def save_products(self, product_plugins: Iterable[BasePlugin]) -> None: ...

    # ---- Load ---------------------------------------------------------------
    @abstractmethod
    def load_parameter(self,
                       plugin_type: str,
                       plugin_name: str,
                       group_name: str,
                       parameter_name: str) -> Optional[BaseParameter]: ...

    @abstractmethod
    def load_plugin_into(self, plugin_type: str, plugin: BasePlugin) -> None: ...

    @abstractmethod
    def load_equipment_into(self, plugin: BasePlugin) -> None: ...

    @abstractmethod
    def load_test_into(self, plugin: BasePlugin) -> None: ...

    @abstractmethod
    def load_product_into(self, plugin: BasePlugin) -> None: ...

    # ---- Query (raw) -------------------------------------------------------
    @abstractmethod
    def load_all_for_type(self, plugin_type: str) -> list[Any]: ...

    # ---- Delete -------------------------------------------------------------
    @abstractmethod
    def delete_plugin(self, plugin_type: str, plugin_name: str) -> None: ...

    @abstractmethod
    def delete_group(self, plugin_type: str, plugin_name: str, group_name: str) -> None: ...

    @abstractmethod
    def delete_parameter(self,
                         plugin_type: str,
                         plugin_name: str,
                         group_name: str,
                         parameter_name: str) -> None: ...

    # ---- Lifecycle ----------------------------------------------------------
    @abstractmethod
    def close(self) -> None: ...

    # ---- Dangerous maintenance --------------------------------------------------------------------------------
    @abstractmethod
    def wipeDB(self) -> None: ...  # Danger: irreversibly remove all persisted parameter data
