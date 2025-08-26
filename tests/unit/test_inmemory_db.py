"""
Unit tests for InMemoryDB implementation.

Tests all BaseDB interface methods and InMemoryDB-specific functionality.
"""

import json
from datetime import datetime
from unittest.mock import Mock

import pytest

from Cerberus.database.inMemoryDB import InMemoryDB


@pytest.fixture
def db():
    """Create a fresh InMemoryDB instance for each test."""
    database = InMemoryDB("test_station")
    yield database
    database.close()


@pytest.fixture
def mock_plugin():
    """Create a mock plugin for testing."""
    plugin = Mock()
    plugin.name = "TestPlugin"

    # Mock parameters
    param1 = Mock()
    param1.value = "test_value_1"
    param2 = Mock()
    param2.value = 42
    param3 = Mock()
    param3.value = True

    # Mock parameter groups
    plugin._groupParams = {
        "connection": {
            "ip_address": param1,
            "port": param2
        },
        "settings": {
            "enabled": param3
        }
    }

    return plugin


@pytest.fixture
def mock_test_result():
    """Create a mock test result for testing."""
    def _create_mock_test_result(name="TestResult", status="Passed"):
        result = Mock()
        result.name = name
        result.status = status
        result.timestanmp = datetime.now()  # Note: keeping the typo for compatibility
        result.log = f"Test {name} completed with status: {status}"
        result.testResult = {"value": 123, "pass": status == "Passed"}
        return result

    return _create_mock_test_result


# ---- Basic Functionality Tests ----

def test_init(db):
    """Test InMemoryDB initialization."""
    assert db.station_id == "test_station"
    assert len(db._plugin_data) == 0
    assert len(db._test_results) == 0
    assert db._next_test_result_id == 1


def test_close():
    """Test database close operation."""
    db = InMemoryDB("test_station")

    # Add some data first
    db._plugin_data["test"]["plugin"]["group"] = {"key": "value"}
    db._test_results["test"] = [{"id": 1}]

    # Close should clear everything
    db.close()

    assert len(db._plugin_data) == 0
    assert len(db._test_results) == 0
    assert db._next_test_result_id == 1


# ---- Plugin Save/Load Tests ----

def test_save_plugin(db, mock_plugin):
    """Test saving a single plugin."""
    db.save_plugin("equipment", mock_plugin)

    # Verify data was saved
    assert "equipment" in db._plugin_data
    assert "TestPlugin" in db._plugin_data["equipment"]

    plugin_data = db._plugin_data["equipment"]["TestPlugin"]
    assert "connection" in plugin_data
    assert "settings" in plugin_data

    assert plugin_data["connection"]["ip_address"] == "test_value_1"
    assert plugin_data["connection"]["port"] == 42
    assert plugin_data["settings"]["enabled"] is True


def test_save_many(db, mock_plugin):
    """Test saving multiple plugins."""
    plugins = [mock_plugin]
    db.save_many("equipment", plugins)

    # Should be same as save_plugin for one plugin
    assert "equipment" in db._plugin_data
    assert "TestPlugin" in db._plugin_data["equipment"]


def test_load_plugin_into(db, mock_plugin):
    """Test loading plugin data."""
    # Save first
    db.save_plugin("equipment", mock_plugin)

    # Create new plugin with different values
    new_plugin = Mock()
    new_plugin.name = "TestPlugin"

    param1 = Mock()
    param1.value = "different"
    param2 = Mock()
    param2.value = 999
    param3 = Mock()
    param3.value = False

    new_plugin._groupParams = {
        "connection": {
            "ip_address": param1,
            "port": param2
        },
        "settings": {
            "enabled": param3
        }
    }

    # Load should update the values
    db.load_plugin_into("equipment", new_plugin)

    assert new_plugin._groupParams["connection"]["ip_address"].value == "test_value_1"
    assert new_plugin._groupParams["connection"]["port"].value == 42


def test_convenience_bulk_helpers(db, mock_plugin):
    """Test convenience methods for bulk operations."""
    plugins = [mock_plugin]

    # Test all bulk save methods
    db.save_equipment(plugins)
    db.save_tests(plugins)
    db.save_products(plugins)

    # Verify data was saved under correct types
    assert "equipment" in db._plugin_data
    assert "test" in db._plugin_data
    assert "product" in db._plugin_data

    # Test load methods
    new_plugin = Mock()
    new_plugin.name = "TestPlugin"
    param = Mock()
    param.value = 999
    new_plugin._groupParams = {"connection": {"port": param}, "settings": {}}

    db.load_equipment_into(new_plugin)
    assert new_plugin._groupParams["connection"]["port"].value == 42


# ---- Delete Operation Tests ----

def test_delete_plugin(db, mock_plugin):
    """Test deleting an entire plugin."""
    db.save_plugin("equipment", mock_plugin)

    # Verify it exists
    assert "TestPlugin" in db._plugin_data["equipment"]

    # Delete it
    db.delete_plugin("equipment", "TestPlugin")

    # Should be gone
    assert "TestPlugin" not in db._plugin_data.get("equipment", {})


def test_delete_group(db, mock_plugin):
    """Test deleting a specific group from a plugin."""
    db.save_plugin("equipment", mock_plugin)

    # Verify both groups exist
    plugin_data = db._plugin_data["equipment"]["TestPlugin"]
    assert "connection" in plugin_data
    assert "settings" in plugin_data

    # Delete one group
    db.delete_group("equipment", "TestPlugin", "connection")

    # Should still have settings but not connection
    assert "connection" not in plugin_data
    assert "settings" in plugin_data


# ---- Test Results Tests ----

def test_save_test_result(db, mock_test_result):
    """Test saving a test result."""
    test_result = mock_test_result()

    result_id = db.save_test_result(test_result)

    assert result_id == 1
    assert db._next_test_result_id == 2

    # Verify result was saved
    assert "testresult" in db._test_results
    results = db._test_results["testresult"]
    assert len(results) == 1

    saved_result = results[0]
    assert saved_result["id"] == 1
    assert saved_result["status"] == "Passed"


def test_save_test_result_with_large_log(db, mock_test_result):
    """Test saving a test result with large log (compression)."""
    test_result = mock_test_result()
    test_result.log = "x" * 2000  # Large log

    result_id = db.save_test_result(test_result)

    # Verify compression was applied
    results = db._test_results["testresult"]
    saved_result = results[0]
    assert saved_result["log_text"] is None
    assert saved_result["compressed_log"] is not None


def test_load_test_results(db, mock_test_result):
    """Test loading test results with pagination."""
    # Save multiple results
    for i in range(5):
        result = mock_test_result(name=f"TestResult_{i}")
        db.save_test_result(result)

    # Load with limit
    results = db.load_test_results("TestResult_0", limit=3)
    assert len(results) == 1  # Only one matches exact name

    # Load all for a generic name pattern (this would need adjustment for real use)
    # For now, test that the method works
    results = db.load_test_results("testresult_0", limit=10)
    assert len(results) == 1


def test_get_test_result_by_id(db, mock_test_result):
    """Test getting a specific test result by ID."""
    test_result = mock_test_result()
    result_id = db.save_test_result(test_result)

    retrieved = db.get_test_result_by_id("TestResult", result_id)

    assert retrieved is not None
    if retrieved:  # Type guard for linter
        assert retrieved["id"] == result_id
        assert retrieved["status"] == "Passed"


def test_delete_test_result(db, mock_test_result):
    """Test deleting a specific test result."""
    test_result = mock_test_result()
    result_id = db.save_test_result(test_result)

    # Verify it exists
    assert db.get_test_result_by_id("TestResult", result_id) is not None

    # Delete it
    deleted = db.delete_test_result("TestResult", result_id)
    assert deleted is True

    # Should be gone
    assert db.get_test_result_by_id("TestResult", result_id) is None


def test_cleanup_old_test_results(db, mock_test_result):
    """Test cleaning up old test results."""
    # Save multiple results for same test
    test_name = "CleanupTest"
    for i in range(10):
        result = mock_test_result(name=test_name)
        db.save_test_result(result)

    # Keep only 3 most recent
    deleted_count = db.cleanup_old_test_results(test_name, keep_count=3)

    assert deleted_count == 7

    # Verify only 3 remain
    clean_name = db._clean_test_name(test_name)
    remaining = db._test_results.get(clean_name, [])
    assert len(remaining) == 3


# ---- Maintenance and Integrity Tests ----

def test_check_group_content_integrity(db, mock_plugin):
    """Test data integrity checking."""
    # Save some valid data
    db.save_plugin("equipment", mock_plugin)

    # Check integrity - should find no issues
    issues = db.check_group_content_integrity()
    assert len(issues) == 0


def test_cleanup_duplicate_group_settings(db):
    """Test duplicate cleanup (should find none by design)."""
    report = db.cleanup_duplicate_group_settings()

    assert report["duplicate_sets"] == 0
    assert report["rows_deleted"] == 0


def test_wipe_db(db, mock_plugin, mock_test_result):
    """Test wiping all data."""
    # Add some data
    db.save_plugin("equipment", mock_plugin)
    test_result = mock_test_result()
    db.save_test_result(test_result)

    # Verify data exists
    assert len(db._plugin_data) > 0
    assert len(db._test_results) > 0

    # Wipe everything
    db.wipe_db()

    # Should be empty
    assert len(db._plugin_data) == 0
    assert len(db._test_results) == 0
    assert db._next_test_result_id == 1


# ---- Utility Method Tests ----

def test_ensure_json_serializable(db):
    """Test JSON serialization safety."""
    # Test with mixed data types
    data = {
        "string": "hello",
        "int": 42,
        "float": 3.14,
        "bool": True,
        "none": None,
        "complex": complex(1, 2)  # Not JSON serializable
    }

    safe_data = db._ensure_json_serializable(data)

    # Complex number should be converted to string
    assert safe_data["complex"] == str(complex(1, 2))
    assert safe_data["string"] == "hello"
    assert safe_data["int"] == 42


def test_clean_test_name(db):
    """Test test name cleaning."""
    # Test various input formats
    test_cases = [
        ("Test Name", "testname"),
        ("Test_Name_123", "test_name_123"),
        ("Test-Name!@#", "testname"),
        ("TX Power Test", "txpowertest")
    ]

    for input_name, expected in test_cases:
        cleaned = db._clean_test_name(input_name)
        assert cleaned == expected


# ---- InMemoryDB-specific Tests ----

def test_get_stats(db):
    """Test statistics gathering."""
    stats = db.get_stats()

    expected_keys = [
        "station_id", "plugin_types", "total_plugins",
        "total_groups", "test_types", "total_test_results",
        "next_test_result_id"
    ]

    for key in expected_keys:
        assert key in stats

    assert stats["station_id"] == "test_station"


def test_export_data(db, mock_plugin, mock_test_result):
    """Test data export functionality."""
    # Add some data
    db.save_plugin("equipment", mock_plugin)
    test_result = mock_test_result()
    db.save_test_result(test_result)

    # Export
    exported = db.export_data()

    # Verify structure
    assert "station_id" in exported
    assert "plugin_data" in exported
    assert "test_results" in exported
    assert "next_test_result_id" in exported

    # Verify content
    assert exported["station_id"] == "test_station"
    assert "equipment" in exported["plugin_data"]


# ---- Error Handling Tests ----

def test_save_test_result_missing_attributes(db):
    """Test that saving test result with missing attributes raises appropriate error."""
    # Create a simple object that only has 'name' attribute
    class IncompleteResult:
        def __init__(self):
            self.name = "Test"

    incomplete_result = IncompleteResult()

    with pytest.raises(ValueError, match="test_result must have attribute 'status'"):
        db.save_test_result(incomplete_result)


def test_get_test_result_by_id_nonexistent(db):
    """Test getting test result with non-existent ID returns None."""
    result = db.get_test_result_by_id("NonExistent", 999)
    assert result is None


def test_delete_test_result_nonexistent(db):
    """Test deleting non-existent test result returns False."""
    deleted = db.delete_test_result("NonExistent", 999)
    assert deleted is False


def test_cleanup_old_test_results_no_results(db):
    """Test cleanup when no test results exist."""
    deleted_count = db.cleanup_old_test_results("NonExistent", keep_count=5)
    assert deleted_count == 0
