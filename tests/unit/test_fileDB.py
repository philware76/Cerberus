"""
Unit tests for the FileDB class.

FileDB is a JSON file-based implementation of the CerberusDB API that provides
persistent storage for plugin parameters without requiring an external database.

This test suite covers:
- Basic initialization and file structure
- Saving and loading plugins with single and multiple parameter groups  
- Convenience methods for equipment, test, and product plugins
- Deletion operations (groups and entire plugins)
- Data integrity and duplicate cleanup functionality
- Edge cases and error conditions
- Thread safety for concurrent access
- Data persistence across database instances
- Integration with real equipment plugins

The FileDB implementation stores data in a JSON file with the following structure:
- group_identities: Maps (station_id, plugin_type, plugin_name, group_name) to IDs
- group_content: Stores parameter content with SHA256 hashes for integrity
- group_settings: Links identities to content, allowing for deduplication
- next_id: Counter for generating unique IDs
"""

import json
import os
import tempfile
from typing import Any, Dict

import pytest

from Cerberus.database.fileDB import FileDB
from Cerberus.plugins.baseParameters import BaseParameter, BaseParameters
from Cerberus.plugins.basePlugin import BasePlugin
from Cerberus.plugins.equipment.simpleEquip.simple1Equipment import \
    SimpleEquip1


class MockParameter(BaseParameter):
    """Mock parameter for testing."""

    def __init__(self, name: str, value: Any = None, units: str = "", description: str | None = None):
        super().__init__(name, value, units, description)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "units": self.units,
            "description": self.description,
            "type": type(self.value).__name__ if self.value is not None else "NoneType"
        }


class MockPlugin(BasePlugin):
    """Mock plugin for testing."""

    def __init__(self, name: str):
        super().__init__(name)

    def initialise(self, init: Any = None) -> bool:
        """Initialize the plugin."""
        return True

    def finalise(self) -> bool:
        """Finalize the plugin."""
        return True

    def add_test_params(self):
        """Add some test parameters."""
        param1 = MockParameter("param1", "test_value", "V", "Test parameter 1")
        param2 = MockParameter("param2", 42, "Hz", "Test parameter 2")
        param3 = MockParameter("param3", True, "", "Test parameter 3")

        test_group = BaseParameters("test_group")
        test_group["param1"] = param1
        test_group["param2"] = param2
        test_group["param3"] = param3

        self._groupParams["test_group"] = test_group

    def add_multiple_groups(self):
        """Add multiple parameter groups."""
        # Group 1
        group1 = BaseParameters("group1")
        group1["freq"] = MockParameter("freq", 100.0, "MHz", "Frequency")
        group1["power"] = MockParameter("power", -10.0, "dBm", "Power")

        # Group 2
        group2 = BaseParameters("group2")
        group2["enabled"] = MockParameter("enabled", True, "", "Enable flag")
        group2["count"] = MockParameter("count", 5, "", "Count value")

        self._groupParams["group1"] = group1
        self._groupParams["group2"] = group2


@pytest.fixture
def temp_db_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
        temp_filename = tf.name
    yield temp_filename
    # Clean up
    if os.path.exists(temp_filename):
        os.unlink(temp_filename)


@pytest.fixture
def filedb(temp_db_file):
    """Create a FileDB instance for testing."""
    db = FileDB("test_station", temp_db_file)
    yield db
    db.close()


@pytest.fixture
def mock_plugin():
    """Create a mock plugin with test parameters."""
    plugin = MockPlugin("test_plugin")
    plugin.add_test_params()
    return plugin


@pytest.fixture
def simple_equipment():
    """Create a SimpleEquip1 instance for testing with real equipment."""
    return SimpleEquip1()


class TestFileDBBasics:
    """Test basic FileDB functionality."""

    def test_filedb_initialization(self, temp_db_file):
        """Test that FileDB initializes correctly."""
        # Remove the temp file first so FileDB creates it
        if os.path.exists(temp_db_file):
            os.unlink(temp_db_file)

        db = FileDB("test_station", temp_db_file)
        assert db.station_id == "test_station"
        assert db.filename == temp_db_file
        assert os.path.exists(temp_db_file)

        # Check that the file has the correct structure
        with open(temp_db_file, 'r') as f:
            data = json.load(f)
            expected_keys = {"group_identities", "group_content", "group_settings", "next_id"}
            assert set(data.keys()) == expected_keys
            assert data["next_id"] == 1

        db.close()

    def test_save_and_load_plugin(self, filedb, mock_plugin):
        """Test saving and loading a plugin."""
        # Save the plugin
        filedb.save_plugin("equipment", mock_plugin)

        # Create a new plugin to load into
        new_plugin = MockPlugin("test_plugin")
        new_plugin.add_test_params()

        # Clear the values
        for param in new_plugin._groupParams["test_group"].values():
            param.value = None

        # Load from database
        filedb.load_plugin_into("equipment", new_plugin)

        # Check that values were loaded correctly
        loaded_values = {name: param.value for name, param in new_plugin._groupParams["test_group"].items()}
        expected_values = {"param1": "test_value", "param2": 42, "param3": True}
        assert loaded_values == expected_values

    def test_save_multiple_groups(self, filedb):
        """Test saving a plugin with multiple parameter groups."""
        plugin = MockPlugin("multi_group_plugin")
        plugin.add_multiple_groups()

        # Save the plugin
        filedb.save_plugin("test", plugin)

        # Load into a new plugin
        new_plugin = MockPlugin("multi_group_plugin")
        new_plugin.add_multiple_groups()

        # Clear values
        for group in new_plugin._groupParams.values():
            for param in group.values():
                param.value = None

        # Load from database
        filedb.load_plugin_into("test", new_plugin)

        # Check group1 values
        group1_values = {name: param.value for name, param in new_plugin._groupParams["group1"].items()}
        assert group1_values == {"freq": 100.0, "power": -10.0}

        # Check group2 values
        group2_values = {name: param.value for name, param in new_plugin._groupParams["group2"].items()}
        assert group2_values == {"enabled": True, "count": 5}


class TestFileDBConvenienceMethods:
    """Test convenience methods for specific plugin types."""

    def test_save_and_load_equipment(self, filedb, mock_plugin):
        """Test equipment-specific save/load methods."""
        filedb.save_equipment([mock_plugin])

        new_plugin = MockPlugin("test_plugin")
        new_plugin.add_test_params()
        for param in new_plugin._groupParams["test_group"].values():
            param.value = None

        filedb.load_equipment_into(new_plugin)

        loaded_values = {name: param.value for name, param in new_plugin._groupParams["test_group"].items()}
        expected_values = {"param1": "test_value", "param2": 42, "param3": True}
        assert loaded_values == expected_values

    def test_save_and_load_tests(self, filedb, mock_plugin):
        """Test test-specific save/load methods."""
        filedb.save_tests([mock_plugin])

        new_plugin = MockPlugin("test_plugin")
        new_plugin.add_test_params()
        for param in new_plugin._groupParams["test_group"].values():
            param.value = None

        filedb.load_test_into(new_plugin)

        loaded_values = {name: param.value for name, param in new_plugin._groupParams["test_group"].items()}
        expected_values = {"param1": "test_value", "param2": 42, "param3": True}
        assert loaded_values == expected_values

    def test_save_and_load_products(self, filedb, mock_plugin):
        """Test product-specific save/load methods."""
        filedb.save_products([mock_plugin])

        new_plugin = MockPlugin("test_plugin")
        new_plugin.add_test_params()
        for param in new_plugin._groupParams["test_group"].values():
            param.value = None

        filedb.load_product_into(new_plugin)

        loaded_values = {name: param.value for name, param in new_plugin._groupParams["test_group"].items()}
        expected_values = {"param1": "test_value", "param2": 42, "param3": True}
        assert loaded_values == expected_values


class TestFileDBDeletion:
    """Test deletion operations."""

    def test_delete_group(self, filedb, mock_plugin):
        """Test deleting a specific group."""
        # Save the plugin
        filedb.save_plugin("equipment", mock_plugin)

        # Delete the group
        filedb.delete_group("equipment", "test_plugin", "test_group")

        # Try to load - should get empty values
        new_plugin = MockPlugin("test_plugin")
        new_plugin.add_test_params()
        for param in new_plugin._groupParams["test_group"].values():
            param.value = None

        filedb.load_plugin_into("equipment", new_plugin)

        loaded_values = {name: param.value for name, param in new_plugin._groupParams["test_group"].items()}
        expected_empty = {"param1": None, "param2": None, "param3": None}
        assert loaded_values == expected_empty

    def test_delete_plugin(self, filedb):
        """Test deleting an entire plugin."""
        plugin = MockPlugin("multi_group_plugin")
        plugin.add_multiple_groups()

        # Save the plugin
        filedb.save_plugin("equipment", plugin)

        # Delete the entire plugin
        filedb.delete_plugin("equipment", "multi_group_plugin")

        # Try to load - should get empty values
        new_plugin = MockPlugin("multi_group_plugin")
        new_plugin.add_multiple_groups()
        for group in new_plugin._groupParams.values():
            for param in group.values():
                param.value = None

        filedb.load_plugin_into("equipment", new_plugin)

        # All groups should be empty
        for group in new_plugin._groupParams.values():
            for param in group.values():
                assert param.value is None


class TestFileDBIntegrity:
    """Test data integrity and consistency checks."""

    def test_check_group_content_integrity(self, filedb, mock_plugin):
        """Test content integrity checking."""
        # Save some data
        filedb.save_plugin("equipment", mock_plugin)

        # Check integrity - should be no mismatches
        mismatches = filedb.check_group_content_integrity()
        assert len(mismatches) == 0

    def test_cleanup_duplicate_group_settings(self, filedb, mock_plugin):
        """Test duplicate cleanup functionality."""
        # Save some data
        filedb.save_plugin("equipment", mock_plugin)

        # Run cleanup - should find no duplicates in a fresh database
        report = filedb.cleanup_duplicate_group_settings(dry_run=True)
        assert report["duplicate_sets"] == 0
        assert report["rows_deleted"] == 0
        assert report["rows_kept"] == 0


class TestFileDBRealEquipment:
    """Test with real equipment plugins."""

    def test_simple_equipment_save_load(self, filedb, simple_equipment):
        """Test saving and loading real SimpleEquip1 equipment."""
        # Save the equipment
        filedb.save_equipment([simple_equipment])

        # Create a new instance to load into
        new_equipment = SimpleEquip1()

        # Load from database
        filedb.load_equipment_into(new_equipment)

        # The equipment should have the same parameter values
        # (Note: we can't easily compare all parameters without knowing the exact structure,
        #  but we can verify that loading doesn't crash and that the plugin has groups)
        assert len(new_equipment._groupParams) > 0


class TestFileDBEdgeCases:
    """Test edge cases and error conditions."""

    def test_load_nonexistent_plugin(self, filedb, mock_plugin):
        """Test loading a plugin that doesn't exist in the database."""
        # Clear the initial values first
        for param in mock_plugin._groupParams["test_group"].values():
            param.value = None

        # Try to load without saving first
        filedb.load_plugin_into("equipment", mock_plugin)

        # Values should remain unchanged (still None since we cleared them)
        for param in mock_plugin._groupParams["test_group"].values():
            assert param.value is None

    def test_delete_nonexistent_plugin(self, filedb):
        """Test deleting a plugin that doesn't exist."""
        # Should not raise an exception
        filedb.delete_plugin("equipment", "nonexistent_plugin")
        filedb.delete_group("equipment", "nonexistent_plugin", "nonexistent_group")

    def test_wipe_db(self, filedb, mock_plugin):
        """Test wiping the entire database."""
        # Save some data
        filedb.save_plugin("equipment", mock_plugin)

        # Wipe the database
        filedb.wipe_db()

        # Try to load - should get empty values
        new_plugin = MockPlugin("test_plugin")
        new_plugin.add_test_params()
        # Clear the initial values
        for param in new_plugin._groupParams["test_group"].values():
            param.value = None

        filedb.load_plugin_into("equipment", new_plugin)

        for param in new_plugin._groupParams["test_group"].values():
            assert param.value is None

    def test_concurrent_access(self, filedb, mock_plugin):
        """Test that concurrent access doesn't corrupt data (basic thread safety)."""
        import threading
        import time

        def save_load_cycle():
            for i in range(10):
                plugin = MockPlugin(f"plugin_{i}")
                plugin.add_test_params()
                filedb.save_plugin("equipment", plugin)
                time.sleep(0.001)  # Small delay to allow interleaving
                filedb.load_plugin_into("equipment", plugin)

        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=save_load_cycle)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # If we get here without exceptions, basic thread safety is working


class TestFileDBPersistence:
    """Test data persistence across database instances."""

    def test_persistence_across_instances(self, temp_db_file, mock_plugin):
        """Test that data persists when creating new FileDB instances."""
        # Save data with first instance
        db1 = FileDB("test_station", temp_db_file)
        db1.save_plugin("equipment", mock_plugin)
        db1.close()

        # Load data with second instance
        db2 = FileDB("test_station", temp_db_file)
        new_plugin = MockPlugin("test_plugin")
        new_plugin.add_test_params()
        for param in new_plugin._groupParams["test_group"].values():
            param.value = None

        db2.load_plugin_into("equipment", new_plugin)

        loaded_values = {name: param.value for name, param in new_plugin._groupParams["test_group"].items()}
        expected_values = {"param1": "test_value", "param2": 42, "param3": True}
        assert loaded_values == expected_values

        db2.close()
