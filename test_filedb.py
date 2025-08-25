#!/usr/bin/env python3
"""
Simple test script to verify FileDB functionality.
"""

from Cerberus.plugins.baseParameters import BaseParameter, BaseParameters
from Cerberus.plugins.basePlugin import BasePlugin
from Cerberus.database.fileDB import FileDB
import os
import tempfile
import json
from typing import Dict, Any

# Add the Cerberus directory to the path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Cerberus'))


class MockParameter(BaseParameter):
    """Mock parameter for testing."""

    def __init__(self, name: str, value: Any = None):
        super().__init__(name, value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
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
        # Add parameters to a group called "test_group"
        param1 = MockParameter("param1", "test_value")
        param2 = MockParameter("param2", 42)
        param3 = MockParameter("param3", True)

        test_group = BaseParameters("test_group")
        test_group["param1"] = param1
        test_group["param2"] = param2
        test_group["param3"] = param3

        self._groupParams["test_group"] = test_group


def test_filedb():
    """Test the FileDB implementation."""
    print("Testing FileDB implementation...")

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
        temp_filename = tf.name

    try:
        # Initialize FileDB
        db = FileDB("test_station", temp_filename)

        # Create a mock plugin
        plugin = MockPlugin("test_plugin")
        plugin.add_test_params()

        print("1. Testing save_plugin...")
        # Save the plugin
        db.save_plugin("equipment", plugin)

        # Verify the file was created and has content
        with open(temp_filename, 'r') as f:
            data = json.load(f)
            print(f"   File structure created: {list(data.keys())}")
            print(f"   Group identities: {len(data['group_identities'])}")
            print(f"   Group content: {len(data['group_content'])}")
            print(f"   Group settings: {len(data['group_settings'])}")

        print("2. Testing load_plugin_into...")
        # Create a new plugin to load into
        new_plugin = MockPlugin("test_plugin")
        new_plugin.add_test_params()

        # Clear the values
        for param in new_plugin._groupParams["test_group"].values():
            param.value = None

        # Load from database
        db.load_plugin_into("equipment", new_plugin)

        # Check that values were loaded
        loaded_values = {name: param.value for name, param in new_plugin._groupParams["test_group"].items()}
        print(f"   Loaded values: {loaded_values}")

        expected_values = {"param1": "test_value", "param2": 42, "param3": True}
        assert loaded_values == expected_values, f"Expected {expected_values}, got {loaded_values}"

        print("3. Testing convenience methods...")
        # Test convenience methods
        db.save_equipment([plugin])
        db.load_equipment_into(new_plugin)

        print("4. Testing delete operations...")
        # Test delete group
        db.delete_group("equipment", "test_plugin", "test_group")

        # Try to load again - should be empty
        new_plugin2 = MockPlugin("test_plugin")
        new_plugin2.add_test_params()
        for param in new_plugin2._groupParams["test_group"].values():
            param.value = None

        db.load_plugin_into("equipment", new_plugin2)
        loaded_after_delete = {name: param.value for name, param in new_plugin2._groupParams["test_group"].items()}
        expected_empty = {"param1": None, "param2": None, "param3": None}
        assert loaded_after_delete == expected_empty, f"Expected {expected_empty}, got {loaded_after_delete}"

        print("5. Testing integrity check...")
        # Test integrity check
        mismatches = db.check_group_content_integrity()
        assert len(mismatches) == 0, f"Expected no mismatches, got {len(mismatches)}"

        print("6. Testing duplicate cleanup...")
        # Test duplicate cleanup
        report = db.cleanup_duplicate_group_settings(dry_run=True)
        print(f"   Duplicate cleanup report: {report}")

        # Close the database
        db.close()

        print("✅ All tests passed!")

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)


if __name__ == "__main__":
    test_filedb()
