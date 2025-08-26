import hashlib
import json
import zlib
from collections import defaultdict
from datetime import datetime
from logging import INFO
from typing import Any, Iterable

from Cerberus.database.baseDB import BaseDB
from Cerberus.logConfig import getLogger
from Cerberus.plugins.basePlugin import BasePlugin

logger = getLogger("InMemoryDB")
logger.setLevel(INFO)


class InMemoryDB(BaseDB):
    """
    In-memory implementation of BaseDB for testing and non-persistent storage.

    This implementation stores all data in memory using Python dictionaries and lists.
    Data is lost when the instance is destroyed or the application shuts down.

    Perfect for:
    - Unit testing
    - Integration testing
    - Temporary storage scenarios
    - Development and debugging
    """

    def __init__(self, station_id: str):
        super().__init__(station_id)

        # Plugin configuration storage: {plugin_type: {plugin_name: {group_name: values_dict}}}
        self._plugin_data: dict[str, dict[str, dict[str, dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))

        # Test results storage: {test_name: [test_result_dicts]}
        self._test_results: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # Counter for generating test result IDs
        self._next_test_result_id = 1

        logger.info(f"InMemoryDB initialized for station: {station_id}")

    def close(self) -> None:
        """Close database connection and clean up resources."""
        # For in-memory DB, just clear the data
        self._plugin_data.clear()
        self._test_results.clear()
        logger.info("InMemoryDB closed and data cleared")

    # ---- Plugin Save/Load Operations ----------------------------------------

    def save_plugin(self, plugin_type: str, plugin: BasePlugin) -> None:
        """Save a single plugin's configuration to memory."""
        for group_name, group in plugin._groupParams.items():
            values = {pname: p.value for pname, p in group.items()}
            safe_values = self._ensure_json_serializable(values)
            self._plugin_data[plugin_type][plugin.name][group_name] = safe_values

        logger.debug(f"Saved plugin: {plugin_type}/{plugin.name}")

    def save_many(self, plugin_type: str, plugins: Iterable[BasePlugin]) -> None:
        """Save multiple plugins of the same type to memory."""
        count = 0
        for plugin in plugins:
            self.save_plugin(plugin_type, plugin)
            count += 1
        logger.debug(f"Saved {count} plugins of type: {plugin_type}")

    def load_plugin_into(self, plugin_type: str, plugin: BasePlugin) -> None:
        """Load plugin configuration from memory into the provided plugin instance."""
        plugin_data = self._plugin_data.get(plugin_type, {}).get(plugin.name, {})

        for group_name, group in plugin._groupParams.items():
            if group_name in plugin_data:
                values = plugin_data[group_name]
                for param_name, param in group.items():
                    if param_name in values:
                        param.value = values[param_name]

        logger.debug(f"Loaded plugin: {plugin_type}/{plugin.name}")

    # ---- Convenience Bulk Helpers -------------------------------------------

    def save_equipment(self, equipment_plugins: Iterable[BasePlugin]) -> None:
        """Save equipment plugin configurations."""
        self.save_many('equipment', equipment_plugins)

    def save_tests(self, test_plugins: Iterable[BasePlugin]) -> None:
        """Save test plugin configurations."""
        self.save_many('test', test_plugins)

    def save_products(self, product_plugins: Iterable[BasePlugin]) -> None:
        """Save product plugin configurations."""
        self.save_many('product', product_plugins)

    def load_equipment_into(self, plugin: BasePlugin) -> None:
        """Load equipment plugin configuration."""
        self.load_plugin_into('equipment', plugin)

    def load_test_into(self, plugin: BasePlugin) -> None:
        """Load test plugin configuration."""
        self.load_plugin_into('test', plugin)

    def load_product_into(self, plugin: BasePlugin) -> None:
        """Load product plugin configuration."""
        self.load_plugin_into('product', plugin)

    # ---- Delete Operations ---------------------------------------------------

    def delete_plugin(self, plugin_type: str, plugin_name: str) -> None:
        """Delete all data for a specific plugin."""
        if plugin_type in self._plugin_data and plugin_name in self._plugin_data[plugin_type]:
            del self._plugin_data[plugin_type][plugin_name]
            logger.debug(f"Deleted plugin: {plugin_type}/{plugin_name}")

    def delete_group(self, plugin_type: str, plugin_name: str, group_name: str) -> None:
        """Delete data for a specific plugin group."""
        plugin_data = self._plugin_data.get(plugin_type, {}).get(plugin_name, {})
        if group_name in plugin_data:
            del plugin_data[group_name]
            logger.debug(f"Deleted group: {plugin_type}/{plugin_name}/{group_name}")

    # ---- Test Results Management ---------------------------------------------

    def save_test_result(self, test_result) -> int:
        """Save a test result to memory.

        Args:
            test_result: BaseTestResult instance or compatible object

        Returns:
            int: The ID of the saved test result record
        """
        # Check if it looks like a BaseTestResult (duck typing approach)
        required_attrs = ['name', 'status', 'timestanmp', 'testResult']
        for attr in required_attrs:
            if not hasattr(test_result, attr):
                raise ValueError(f"test_result must have attribute '{attr}' (BaseTestResult-like object required)")

        # Clean test name
        clean_test_name = self._clean_test_name(test_result.name)

        # Generate unique ID
        result_id = self._next_test_result_id
        self._next_test_result_id += 1

        # Prepare log data (compress if large)
        log_data = getattr(test_result, 'log', None) or ""
        compressed_log = None
        if len(log_data) > 1024:
            compressed_log = zlib.compress(log_data.encode('utf-8'))
            log_data = None  # Clear uncompressed data

        # Convert testResult dictionary to JSON
        test_result_json = json.dumps(test_result.testResult, default=str, sort_keys=True)

        # Create result record
        result_record = {
            'id': result_id,
            'test_name': clean_test_name,
            'status': test_result.status.value if hasattr(test_result.status, 'value') else str(test_result.status),
            'timestamp': test_result.timestanmp,
            'log_text': log_data,
            'compressed_log': compressed_log,
            'test_result_json': test_result_json
        }

        # Store in memory
        self._test_results[clean_test_name].append(result_record)

        logger.debug(f"Saved test result: {clean_test_name} (ID: {result_id})")
        return result_id

    def load_test_results(self, test_name: str, limit: int = 100, offset: int = 0) -> list[dict]:
        """Load test results from memory.

        Args:
            test_name: Name of the test (e.g., "TxLevel")
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of test result dictionaries
        """
        clean_test_name = self._clean_test_name(test_name)
        results = self._test_results.get(clean_test_name, [])

        # Sort by timestamp (newest first) and apply pagination
        sorted_results = sorted(results, key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        paginated_results = sorted_results[offset:offset + limit]

        # Decompress logs if needed for return
        for result in paginated_results:
            if result.get('compressed_log'):
                result['log_text'] = self._decompress_log(result['compressed_log'])
                result['compressed_log'] = None  # Don't return compressed data

        logger.debug(f"Loaded {len(paginated_results)} test results for: {clean_test_name}")
        return paginated_results

    def get_test_result_by_id(self, test_name: str, result_id: int) -> dict | None:
        """Get a specific test result by its ID.

        Args:
            test_name: Name of the test
            result_id: ID of the test result

        Returns:
            Test result dictionary or None if not found
        """
        clean_test_name = self._clean_test_name(test_name)
        results = self._test_results.get(clean_test_name, [])

        for result in results:
            if result.get('id') == result_id:
                # Make a copy and decompress log if needed
                result_copy = result.copy()
                if result_copy.get('compressed_log'):
                    result_copy['log_text'] = self._decompress_log(result_copy['compressed_log'])
                    result_copy['compressed_log'] = None
                return result_copy

        return None

    def delete_test_result(self, test_name: str, result_id: int) -> bool:
        """Delete a specific test result.

        Args:
            test_name: Name of the test
            result_id: ID of the test result to delete

        Returns:
            True if deleted, False if not found
        """
        clean_test_name = self._clean_test_name(test_name)
        results = self._test_results.get(clean_test_name, [])

        for i, result in enumerate(results):
            if result.get('id') == result_id:
                del results[i]
                logger.debug(f"Deleted test result: {clean_test_name} (ID: {result_id})")
                return True

        return False

    def cleanup_old_test_results(self, test_name: str, keep_count: int = 1000) -> int:
        """Clean up old test results, keeping only the most recent ones.

        Args:
            test_name: Name of the test
            keep_count: Number of most recent results to keep

        Returns:
            Number of results deleted
        """
        clean_test_name = self._clean_test_name(test_name)
        results = self._test_results.get(clean_test_name, [])

        if len(results) <= keep_count:
            return 0

        # Sort by timestamp (newest first)
        sorted_results = sorted(results, key=lambda x: x.get('timestamp', datetime.min), reverse=True)

        # Keep only the most recent
        kept_results = sorted_results[:keep_count]
        deleted_count = len(results) - len(kept_results)

        # Update storage
        self._test_results[clean_test_name] = kept_results

        logger.debug(f"Cleaned up {deleted_count} old test results for: {clean_test_name}")
        return deleted_count

    # ---- Database Maintenance and Integrity ----------------------------------

    def check_group_content_integrity(self) -> list[tuple[int, str, str]]:
        """Verify database content integrity.

        For InMemoryDB, this checks that all stored JSON can be re-serialized consistently.

        Returns:
            List of (content_id, stored_hash, recomputed_hash) for mismatches.
            Empty list means all data is valid.
        """
        mismatches: list[tuple[int, str, str]] = []
        total_checked = 0

        # Check all plugin data
        for plugin_type, plugins in self._plugin_data.items():
            for plugin_name, groups in plugins.items():
                for group_name, values in groups.items():
                    total_checked += 1
                    content_id = hash((plugin_type, plugin_name, group_name))  # Simple ID for in-memory

                    try:
                        # Try to serialize and hash the data
                        canonical_json = json.dumps(values, sort_keys=True, separators=(",", ":"))
                        computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
                        stored_hash = computed_hash  # In memory, these should always match

                        # For demonstration, we could introduce artificial mismatches here
                        # but in a clean in-memory implementation, there should be none

                    except Exception as e:
                        # If we can't serialize the data, that's a problem
                        mismatches.append((content_id, "unknown", f"serialization_error: {e}"))

        if mismatches:
            logger.warning(f"Content integrity check: {len(mismatches)}/{total_checked} issues detected.")
        else:
            logger.info(f"Content integrity check: all {total_checked} items verified.")

        return mismatches

    def cleanup_duplicate_group_settings(self, dry_run: bool = False) -> dict[str, Any]:
        """Detect and optionally remove duplicate settings.

        For InMemoryDB, duplicates should not occur by design, but this method
        provides the interface for consistency.

        Args:
            dry_run: If True, no modifications are made; only a report is returned.

        Returns:
            Report dictionary containing counts and details of duplicates found/removed.
        """
        # In-memory implementation shouldn't have duplicates by design
        report = {
            "duplicate_sets": 0,
            "rows_deleted": 0,
            "rows_kept": 0,
            "details": [],
            "dry_run": dry_run
        }

        logger.info("Duplicate cleanup: InMemoryDB has no duplicates by design")
        return report

    # ---- Lifecycle and Dangerous Operations ----------------------------------

    def wipe_db(self) -> None:
        """Very dangerous: clear all data from memory.

        This will irreversibly remove all persisted data in this instance.
        """
        self._plugin_data.clear()
        self._test_results.clear()
        self._next_test_result_id = 1
        logger.warning("InMemoryDB wiped - all data cleared")

    # ---- Utility Methods -----------------------------------------------------

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
    def _clean_test_name(test_name: str) -> str:
        """Clean test name for use as a key.

        Args:
            test_name: Original test name

        Returns:
            Cleaned test name safe for use as dictionary key
        """
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

    # ---- Debug and Inspection Methods ----------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the in-memory database.

        Returns:
            Dictionary with statistics about stored data
        """
        plugin_count = 0
        group_count = 0
        test_result_count = 0

        for plugin_type, plugins in self._plugin_data.items():
            plugin_count += len(plugins)
            for plugin_name, groups in plugins.items():
                group_count += len(groups)

        for test_name, results in self._test_results.items():
            test_result_count += len(results)

        return {
            "station_id": self.station_id,
            "plugin_types": len(self._plugin_data),
            "total_plugins": plugin_count,
            "total_groups": group_count,
            "test_types": len(self._test_results),
            "total_test_results": test_result_count,
            "next_test_result_id": self._next_test_result_id
        }

    def export_data(self) -> dict[str, Any]:
        """Export all data as a JSON-serializable dictionary.

        Useful for debugging or creating snapshots.

        Returns:
            Dictionary containing all stored data
        """
        # Convert test results to JSON-serializable format
        serializable_test_results = {}
        for test_name, results in self._test_results.items():
            serializable_results = []
            for result in results:
                serialized_result = result.copy()
                # Convert compressed logs to base64 for JSON serialization
                if serialized_result.get('compressed_log'):
                    import base64
                    serialized_result['compressed_log_b64'] = base64.b64encode(
                        serialized_result['compressed_log']
                    ).decode('ascii')
                    del serialized_result['compressed_log']
                # Convert datetime to ISO string
                if serialized_result.get('timestamp'):
                    serialized_result['timestamp'] = serialized_result['timestamp'].isoformat()
                serializable_results.append(serialized_result)
            serializable_test_results[test_name] = serializable_results

        return {
            "station_id": self.station_id,
            "plugin_data": dict(self._plugin_data),
            "test_results": serializable_test_results,
            "next_test_result_id": self._next_test_result_id
        }
