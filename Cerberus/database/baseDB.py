from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Iterable

from Cerberus.plugins.basePlugin import BasePlugin


class BaseDB(ABC):
    """
    Abstract interface for generic plugin parameter persistence.
    This provides the public API that can be implemented by concrete database backends
    or used for testing and mocking purposes.

    Implementations:
      - CerberusDB: Abstract base with common logic for SQL backends
      - MySqlDB: MySQL implementation  
      - PostgreSqlDB: PostgreSQL implementation
      - Future: FileDB, InMemoryDB for testing
    """

    def __init__(self, station_id: str):
        self.station_id = station_id

    # ---- Plugin Save/Load Operations ----------------------------------------
    @abstractmethod
    def save_plugin(self, plugin_type: str, plugin: BasePlugin) -> None:
        """Save a single plugin's configuration to the database."""
        ...

    @abstractmethod
    def save_many(self, plugin_type: str, plugins: Iterable[BasePlugin]) -> None:
        """Save multiple plugins of the same type to the database."""
        ...

    @abstractmethod
    def load_plugin_into(self, plugin_type: str, plugin: BasePlugin) -> None:
        """Load plugin configuration from database into the provided plugin instance."""
        ...

    # ---- Convenience Bulk Helpers -------------------------------------------
    @abstractmethod
    def save_equipment(self, equipment_plugins: Iterable[BasePlugin]) -> None:
        """Save equipment plugin configurations."""
        ...

    @abstractmethod
    def save_tests(self, test_plugins: Iterable[BasePlugin]) -> None:
        """Save test plugin configurations."""
        ...

    @abstractmethod
    def save_products(self, product_plugins: Iterable[BasePlugin]) -> None:
        """Save product plugin configurations."""
        ...

    @abstractmethod
    def load_equipment_into(self, plugin: BasePlugin) -> None:
        """Load equipment plugin configuration."""
        ...

    @abstractmethod
    def load_test_into(self, plugin: BasePlugin) -> None:
        """Load test plugin configuration."""
        ...

    @abstractmethod
    def load_product_into(self, plugin: BasePlugin) -> None:
        """Load product plugin configuration."""
        ...

    # ---- Delete Operations ---------------------------------------------------
    @abstractmethod
    def delete_plugin(self, plugin_type: str, plugin_name: str) -> None:
        """Delete all data for a specific plugin."""
        ...

    @abstractmethod
    def delete_group(self, plugin_type: str, plugin_name: str, group_name: str) -> None:
        """Delete data for a specific plugin group."""
        ...

    # ---- Test Results Management ---------------------------------------------
    @abstractmethod
    def save_test_result(self, test_result) -> int:
        """Save a test result to the database.

        Args:
            test_result: BaseTestResult instance

        Returns:
            int: The ID of the saved test result record
        """
        ...

    @abstractmethod
    def load_test_results(self, test_name: str, limit: int = 100, offset: int = 0) -> list[dict]:
        """Load test results from the database.

        Args:
            test_name: Name of the test (e.g., "TxLevel")
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of test result dictionaries
        """
        ...

    @abstractmethod
    def get_test_result_by_id(self, test_name: str, result_id: int) -> dict | None:
        """Get a specific test result by its ID.

        Args:
            test_name: Name of the test
            result_id: ID of the test result

        Returns:
            Test result dictionary or None if not found
        """
        ...

    @abstractmethod
    def delete_test_result(self, test_name: str, result_id: int) -> bool:
        """Delete a specific test result.

        Args:
            test_name: Name of the test
            result_id: ID of the test result to delete

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    def cleanup_old_test_results(self, test_name: str, keep_count: int = 1000) -> int:
        """Clean up old test results, keeping only the most recent ones.

        Args:
            test_name: Name of the test
            keep_count: Number of most recent results to keep

        Returns:
            Number of results deleted
        """
        ...

    # ---- Database Maintenance and Integrity ----------------------------------
    @abstractmethod
    def check_group_content_integrity(self) -> list[tuple[int, str, str]]:
        """Verify database content integrity.

        Returns:
            List of (content_id, stored_hash, recomputed_hash) for mismatches.
            Empty list means all rows verified.
        """
        ...

    @abstractmethod
    def cleanup_duplicate_group_settings(self, dry_run: bool = False) -> dict[str, Any]:
        """Detect and optionally remove duplicate settings.

        Args:
            dry_run: If True, no modifications are made; only a report is returned.

        Returns:
            Report dictionary containing counts and details of duplicates found/removed.
        """
        ...

    # ---- Lifecycle and Dangerous Operations ----------------------------------
    @abstractmethod
    def close(self) -> None:
        """Close database connection and clean up resources."""
        ...

    @abstractmethod
    def wipe_db(self) -> None:
        """Very dangerous: drop all Cerberus-related tables from the database.

        This will irreversibly remove all persisted data. Callers should require 
        explicit confirmation before invoking.
        """
        ...

    @abstractmethod
    def wipe_DB(self) -> None:
        """Legacy alias for wipe_db(). 

        Very dangerous: drop all Cerberus-related tables from the database.
        This will irreversibly remove all persisted data.
        """
        ...
