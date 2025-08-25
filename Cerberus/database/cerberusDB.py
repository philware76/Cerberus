import hashlib
import json
import logging
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, cast

from Cerberus.database.baseDB import BaseDB
from Cerberus.logConfig import getLogger
from Cerberus.plugins.baseParameters import BaseParameter
from Cerberus.plugins.basePlugin import BasePlugin

logger = getLogger("CerberusDB")
logger.setLevel(logging.INFO)


@dataclass
class SettingRecord:
    id: int
    station_id: str
    plugin_type: str  # 'equipment' | 'product' | 'test'
    plugin_name: str
    group_name: str
    group_json: str
    param_hash: str

    def key(self) -> tuple[str, str, str, str]:
        return (self.station_id, self.plugin_type, self.plugin_name, self.group_name)


class CerberusDB(BaseDB, ABC):
    """
    Abstract base class for Cerberus DB implementations.
    Base class for shared Cerberus DB logic (MySQL, PostgreSQL, etc).
    Implements common helpers and high-level logic.
    Subclasses must implement DB-specific SQL and connection logic.
    """

    def __init__(self, station_id: str):
        self.station_id = station_id

    def close(self):
        """Close database connection."""
        self._close_impl()

    @staticmethod
    def _canonical_json(d: dict) -> str:
        """Return a deterministic JSON string for hashing (sorted keys, no spaces)."""
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    @classmethod
    def compute_param_hash(cls, param: BaseParameter) -> tuple[str, str]:
        """Compute the SHA256 hex digest for a parameter's JSON representation.
        Returns (hash_hex, canonical_json_string)
        """
        pdata = param.to_dict()
        canonical = cls._canonical_json(pdata)
        h = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return h, canonical

    @classmethod
    def compute_group_hash(cls, values_map: dict) -> tuple[str, str]:
        """Compute SHA256 hash and canonical JSON for a mapping of parameter_name -> value."""
        canonical = cls._canonical_json(values_map)
        h = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return h, canonical

    @staticmethod
    def _ensure_json_serializable(values: dict) -> dict:
        """Return a copy of values where any non-JSON-serializable values are converted to strings."""
        safe: dict = {}
        for k, v in values.items():
            try:
                json.dumps(v)
                safe[k] = v
            except TypeError:
                safe[k] = str(v)
        return safe

    @staticmethod
    def compute_hash_from_json(group_json: str) -> str:
        """Compute SHA256 hash for an arbitrary parameter JSON string."""
        try:
            data = json.loads(group_json)
        except Exception:
            return hashlib.sha256(group_json.encode("utf-8")).hexdigest()
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def save_plugin(self, plugin_type: str, plugin: BasePlugin):
        for group_name, group in plugin._groupParams.items():
            values = {pname: p.value for pname, p in group.items()}
            safe_values = self._ensure_json_serializable(values)
            self._save_group_imp(plugin_type, plugin.name, group_name, safe_values)

    def save_many(self, plugin_type: str, plugins: Iterable[BasePlugin]):
        for p in plugins:
            self.save_plugin(plugin_type, p)

    def load_plugin_into(self, plugin_type: str, plugin: BasePlugin):
        for group_name, group in plugin._groupParams.items():
            mapping = self._load_group_json(plugin_type, plugin.name, group_name)
            if mapping:
                for param_name, param in group.items():
                    if param_name in mapping:
                        param.value = mapping[param_name]

    def delete_plugin(self, plugin_type: str, plugin_name: str):
        """Delete all data for a specific plugin."""
        self._delete_plugin_impl(plugin_type, plugin_name)

    def delete_group(self, plugin_type: str, plugin_name: str, group_name: str):
        """Delete data for a specific plugin group."""
        self._delete_group_impl(plugin_type, plugin_name, group_name)

    def wipe_db(self) -> None:
        """Very dangerous: drop Cerberus-related tables from the connected database.

        This will irreversibly remove persisted data. Callers should require explicit
        confirmation before invoking.
        """
        tables = self._get_cerberus_tables()
        self._drop_tables_safely(tables)

    def wipeDB(self) -> None:
        """Very dangerous: drop Cerberus-related tables from the connected database.

        This will irreversibly remove persisted data. Callers should require explicit
        confirmation before invoking.

        Note: This method delegates to wipe_db() for compatibility.
        """
        self.wipe_db()

    # Convenience bulk helpers
    def save_equipment(self, equipment_plugins: Iterable[BasePlugin]):
        """Save equipment plugin configurations."""
        self.save_many('equipment', equipment_plugins)

    def save_tests(self, test_plugins: Iterable[BasePlugin]):
        """Save test plugin configurations."""
        self.save_many('test', test_plugins)

    def save_products(self, product_plugins: Iterable[BasePlugin]):
        """Save product plugin configurations."""
        self.save_many('product', product_plugins)

    def load_equipment_into(self, plugin: BasePlugin):
        """Load equipment plugin configuration."""
        self.load_plugin_into('equipment', plugin)

    def load_test_into(self, plugin: BasePlugin):
        """Load test plugin configuration."""
        self.load_plugin_into('test', plugin)

    def load_product_into(self, plugin: BasePlugin):
        """Load product plugin configuration."""
        self.load_plugin_into('product', plugin)

    def check_group_content_integrity(self) -> list[tuple[int, str, str]]:
        """Verify each row in group_content matches its stored SHA256 hash.

        Returns list of (content_id, stored_hash, recomputed_hash) for mismatches.
        Empty list means all rows verified. Warns via logging on mismatch.
        """
        # Import here to avoid circular imports
        from Cerberus.logConfig import getLogger
        logger = getLogger("Database")

        # Get raw data from database-specific implementation
        rows = self._get_group_content_rows()

        mismatches: list[tuple[int, str, str]] = []
        total = 0

        for cid_raw, stored_hash_raw, group_json in rows:
            # Assume DB returns correct types; coerce to str/int defensively
            try:
                cid: int = int(cast(Any, cid_raw))
            except Exception:
                continue
            stored_hash = str(stored_hash_raw)
            total += 1

            # group_json may arrive as dict (already decoded) or string
            try:
                if isinstance(group_json, (dict, list)):
                    obj = group_json
                elif isinstance(group_json, (bytes, bytearray, memoryview)):
                    obj = json.loads(bytes(group_json).decode('utf-8'))
                else:
                    obj = json.loads(str(group_json))
            except Exception:
                mismatches.append((cid, stored_hash, '<unparseable>'))
                continue

            canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
            recomputed = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
            if recomputed != stored_hash:
                mismatches.append((cid, stored_hash, recomputed))

        if mismatches:
            logger.warning(
                f"Group content integrity check: {len(mismatches)}/{total} mismatches detected."
            )
        else:
            logger.info(f"Group content integrity check: all {total} rows verified.")

        return mismatches

    def cleanup_duplicate_group_settings(self, dry_run: bool = False) -> dict[str, Any]:
        """Detect and (optionally) remove legacy duplicate rows in group_settings.

        This method provides the business logic for duplicate cleanup, delegating
        database-specific operations to abstract methods.

        Args:
            dry_run: If True, no modifications are committed; a report is returned only.

        Returns a report dict containing counts and per-duplicate details.
        """
        report: dict[str, Any] = {
            "duplicate_sets": 0,
            "rows_deleted": 0,
            "rows_kept": 0,
            "details": []
        }

        # Find duplicate rows (database-specific)
        dup_rows = self._find_duplicate_group_settings_impl()
        if not dup_rows:
            return report

        report["duplicate_sets"] = len(dup_rows)

        # Process duplicates (business logic + database-specific operations)
        total_deleted, total_kept, details = self._process_duplicate_sets_business_logic(dup_rows, dry_run)

        # Build final report
        report.update({
            "rows_deleted": total_deleted,
            "rows_kept": total_kept,
            "details": details,
            "dry_run": dry_run,
        })

        self._log_duplicate_cleanup_report(report, total_kept, total_deleted)
        return report

    def _process_duplicate_sets_business_logic(self, dup_rows: list[Any], dry_run: bool) -> tuple[int, int, list[dict[str, Any]]]:
        """Business logic for processing duplicate sets."""
        total_deleted = 0
        total_kept = 0
        details: list[dict[str, Any]] = []

        for row_data in dup_rows:
            # Parse and validate row data (business logic)
            parsed_data = self._parse_duplicate_row_data_business_logic(row_data)
            if not parsed_data:
                continue

            group_identity_id, content_id, keep_id_int, dup_ids = parsed_data
            total_kept += 1

            # Cleanup single duplicate set (database-specific)
            deleted_this = self._cleanup_single_duplicate_set_impl(group_identity_id, keep_id_int, dup_ids, dry_run)
            total_deleted += deleted_this

            # Record details for this duplicate set (business logic)
            details.append({
                "group_identity_id": group_identity_id,
                "content_id": content_id,
                "keep_id": keep_id_int,
                "duplicate_ids": dup_ids,
                "deleted": deleted_this if not dry_run else 0
            })

        return total_deleted, total_kept, details

    def _parse_duplicate_row_data_business_logic(self, row_data: Any) -> tuple[int, int, int, list[int]] | None:
        """Parse and validate duplicate row data. Returns None if invalid."""
        try:
            # Unpack row data - format may vary by database but logic is the same
            group_identity_id_raw, content_id_raw, cnt_raw, keep_id_raw, all_ids_raw = row_data[:5]

            group_identity_id = int(cast(Any, group_identity_id_raw))
            content_id = int(cast(Any, content_id_raw))
            keep_id = int(cast(Any, keep_id_raw))
        except Exception:
            return None

        all_ids = str(all_ids_raw)
        try:
            # Parse comma-separated ID list (common format across databases)
            id_list = [int(x) for x in all_ids.split(',') if x]
        except Exception:
            return None

        if not id_list:
            return None

        dup_ids = [i for i in id_list if i != keep_id]
        return group_identity_id, content_id, keep_id, dup_ids

    def _log_duplicate_cleanup_report(self, report: dict[str, Any], total_kept: int, total_deleted: int) -> None:
        """Log the duplicate cleanup report."""
        # Import here to avoid circular imports
        from Cerberus.logConfig import getLogger
        logger = getLogger("Database")

        level = logger.info if total_deleted == 0 else logger.warning
        level(
            f"Duplicate cleanup report: sets={report['duplicate_sets']} kept={total_kept} "
            f"deleted={total_deleted} dry_run={report['dry_run']}"
        )

    # ===== TEST RESULTS MANAGEMENT =====

    def save_test_result(self, test_result) -> int:
        """Save a test result to the database.

        Args:
            test_result: BaseTestResult instance

        Returns:
            int: The ID of the saved test result record
        """
        # Import here to avoid circular imports
        from Cerberus.plugins.tests.baseTestResult import BaseTestResult

        if not isinstance(test_result, BaseTestResult):
            raise ValueError("test_result must be a BaseTestResult instance")

        # Compress log if it's large (> 1KB)
        log_data = test_result.log or ""
        compressed_log = None
        if len(log_data) > 1024:
            compressed_log = zlib.compress(log_data.encode('utf-8'))
            log_data = None  # Clear uncompressed data

        # Convert testResult dictionary to JSON
        test_result_json = json.dumps(test_result.testResult, default=str, sort_keys=True)

        # Get clean test name for table naming
        clean_test_name = self._clean_test_name(test_result.name)

        return self._save_test_result_impl(
            test_name=clean_test_name,
            status=test_result.status.value if hasattr(test_result.status, 'value') else str(test_result.status),
            timestamp=test_result.timestanmp,
            log_text=log_data,
            compressed_log=compressed_log,
            test_result_json=test_result_json
        )

    def load_test_results(self, test_name: str, limit: int = 100, offset: int = 0) -> list[dict]:
        """Load test results from the database.

        Args:
            test_name: Name of the test (e.g., "TxLevel")
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of test result dictionaries
        """
        clean_test_name = self._clean_test_name(test_name)
        return self._load_test_results_impl(clean_test_name, limit, offset)

    def get_test_result_by_id(self, test_name: str, result_id: int) -> dict | None:
        """Get a specific test result by its ID.

        Args:
            test_name: Name of the test
            result_id: ID of the test result

        Returns:
            Test result dictionary or None if not found
        """
        clean_test_name = self._clean_test_name(test_name)
        return self._get_test_result_by_id_impl(clean_test_name, result_id)

    def delete_test_result(self, test_name: str, result_id: int) -> bool:
        """Delete a specific test result.

        Args:
            test_name: Name of the test
            result_id: ID of the test result to delete

        Returns:
            True if deleted, False if not found
        """
        clean_test_name = self._clean_test_name(test_name)
        return self._delete_test_result_impl(clean_test_name, result_id)

    def cleanup_old_test_results(self, test_name: str, keep_count: int = 1000) -> int:
        """Clean up old test results, keeping only the most recent ones.

        Args:
            test_name: Name of the test
            keep_count: Number of most recent results to keep

        Returns:
            Number of results deleted
        """
        clean_test_name = self._clean_test_name(test_name)
        return self._cleanup_old_test_results_impl(clean_test_name, keep_count)

    @staticmethod
    def _clean_test_name(test_name: str) -> str:
        """Clean test name for use in table names.

        Args:
            test_name: Original test name

        Returns:
            Cleaned test name safe for table naming
        """
        # Remove spaces, special characters, and convert to lowercase
        import re
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '', test_name)
        return cleaned.lower()

    @staticmethod
    def _decompress_log(compressed_log: bytes) -> str:
        """Decompress a compressed log.

        Args:
            compressed_log: Compressed log data

        Returns:
            Decompressed log text
        """
        try:
            return zlib.decompress(compressed_log).decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to decompress log: {e}")
            return "[Log decompression failed]"

    # Database-specific methods that must be implemented by subclasses:
    @abstractmethod
    def _find_duplicate_group_settings_impl(self) -> list[Any]:
        """Database-specific implementation to find duplicate group settings."""
        raise NotImplementedError

    @abstractmethod
    def _cleanup_single_duplicate_set_impl(self, group_identity_id: int, keep_id_int: int,
                                           dup_ids: list[int], dry_run: bool) -> int:
        """Database-specific implementation to cleanup a single duplicate set.

        Returns number of rows deleted.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_group_content_rows(self) -> list[tuple[Any, Any, Any]]:
        """Get all rows from group_content table.

        Returns list of (id, group_hash, group_json) tuples.
        """
        raise NotImplementedError

    @abstractmethod
    def _close_impl(self):
        """Database-specific implementation for closing connection."""
        raise NotImplementedError

    @abstractmethod
    def _get_cerberus_tables(self) -> list[str]:
        """Return list of Cerberus table names for this database type."""
        raise NotImplementedError

    @abstractmethod
    def _delete_plugin_impl(self, plugin_type: str, plugin_name: str):
        """Database-specific implementation for deleting a plugin."""
        raise NotImplementedError

    @abstractmethod
    def _delete_group_impl(self, plugin_type: str, plugin_name: str, group_name: str):
        """Database-specific implementation for deleting a group."""
        raise NotImplementedError

    @abstractmethod
    def _drop_tables_safely(self, tables: list[str]) -> None:
        """Database-specific implementation for safely dropping multiple tables."""
        raise NotImplementedError

    # The following must be implemented by subclasses:
    @abstractmethod
    def _save_group_imp(self, plugin_type: str, plugin_name: str, group_name: str, values_map: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def _load_group_json(self, plugin_type: str, plugin_name: str, group_name: str) -> dict:
        raise NotImplementedError

    # ===== TEST RESULTS ABSTRACT METHODS =====

    @abstractmethod
    def _save_test_result_impl(self, test_name: str, status: str, timestamp: datetime,
                               log_text: str | None, compressed_log: bytes | None,
                               test_result_json: str) -> int:
        """Database-specific implementation for saving test results.

        Args:
            test_name: Clean test name for table/storage naming
            status: Test result status (e.g., "Passed", "Failed")
            timestamp: When the test was run
            log_text: Uncompressed log text (for small logs < 1KB), or None if compressed
            compressed_log: Compressed log bytes (for large logs >= 1KB), or None if uncompressed
            test_result_json: JSON string of the testResult dictionary

        Note: Either log_text OR compressed_log will be provided, never both.
        - Small logs (< 1KB): log_text contains the actual text, compressed_log is None
        - Large logs (>= 1KB): compressed_log contains zlib-compressed bytes, log_text is None

        Returns the ID of the saved test result record.
        """
        raise NotImplementedError

    @abstractmethod
    def _load_test_results_impl(self, test_name: str, limit: int, offset: int) -> list[dict]:
        """Database-specific implementation for loading test results."""
        raise NotImplementedError

    @abstractmethod
    def _get_test_result_by_id_impl(self, test_name: str, result_id: int) -> dict | None:
        """Database-specific implementation for getting test result by ID."""
        raise NotImplementedError

    @abstractmethod
    def _delete_test_result_impl(self, test_name: str, result_id: int) -> bool:
        """Database-specific implementation for deleting a test result."""
        raise NotImplementedError

    @abstractmethod
    def _cleanup_old_test_results_impl(self, test_name: str, keep_count: int) -> int:
        """Database-specific implementation for cleaning up old test results."""
        raise NotImplementedError
