"""
Example usage and basic test of InMemoryDB implementation.

This demonstrates how to use InMemoryDB for testing and temporary storage scenarios.
"""

from Cerberus.database.inMemoryDB import InMemoryDB
import json
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def demo_inmemory_db():
    """Demonstrate basic InMemoryDB functionality."""

    print("=== InMemoryDB Demo ===")

    # Create an in-memory database instance
    db = InMemoryDB("test_station_001")

    # Show initial stats
    print(f"Initial stats: {json.dumps(db.get_stats(), indent=2)}")

    # Example: Save some mock plugin data
    print("\n1. Saving mock plugin data...")

    # Mock plugin data structure
    mock_equipment_data = {
        "SpectrumAnalyzer": {
            "connection": {
                "ip_address": "192.168.1.100",
                "port": 5025,
                "timeout": 30
            },
            "settings": {
                "frequency_start": 1000000,
                "frequency_stop": 6000000000,
                "resolution_bandwidth": 1000
            }
        },
        "PowerMeter": {
            "connection": {
                "ip_address": "192.168.1.101",
                "port": 5025
            },
            "calibration": {
                "offset_db": -0.5,
                "last_cal_date": "2024-01-15"
            }
        }
    }

    # Simulate saving plugin data
    for plugin_type in ["equipment", "test", "product"]:
        for plugin_name, groups in mock_equipment_data.items():
            for group_name, values in groups.items():
                # Create the nested structure if it doesn't exist
                if plugin_type not in db._plugin_data:
                    db._plugin_data[plugin_type] = {}
                if plugin_name not in db._plugin_data[plugin_type]:
                    db._plugin_data[plugin_type][plugin_name] = {}

                db._plugin_data[plugin_type][plugin_name][group_name] = values

    print("✓ Plugin data saved")

    # Example: Save some mock test results
    print("\n2. Saving mock test results...")

    # Create mock test result objects
    mock_test_results = [
        {
            "name": "TxPowerTest",
            "status": "Passed",
            "timestanmp": datetime.now(),  # Note: keeping the typo for compatibility
            "log": "Test completed successfully. Power level: 23.5 dBm",
            "testResult": {"power_dbm": 23.5, "frequency_hz": 2400000000, "pass": True}
        },
        {
            "name": "TxPowerTest",
            "status": "Failed",
            "timestanmp": datetime.now(),
            "log": "Test failed. Power level too low: 18.2 dBm (expected > 20 dBm)",
            "testResult": {"power_dbm": 18.2, "frequency_hz": 2400000000, "pass": False}
        },
        {
            "name": "RxSensitivityTest",
            "status": "Passed",
            "timestanmp": datetime.now(),
            "log": "Sensitivity test passed. Minimum detectable signal: -95 dBm",
            "testResult": {"sensitivity_dbm": -95, "frequency_hz": 2400000000, "pass": True}
        }
    ]

    # Mock BaseTestResult class for demonstration
    class MockTestResult:
        def __init__(self, data):
            self.name = data["name"]
            self.status = data["status"]
            self.timestanmp = data["timestanmp"]
            self.log = data["log"]
            self.testResult = data["testResult"]

    # Save test results
    saved_ids = []
    for result_data in mock_test_results:
        # For demo purposes, we'll directly add to the internal storage
        # In real usage, you'd use db.save_test_result() with proper BaseTestResult objects
        test_name = db._clean_test_name(result_data["name"])
        result_id = db._next_test_result_id
        db._next_test_result_id += 1

        result_record = {
            'id': result_id,
            'test_name': test_name,
            'status': result_data["status"],
            'timestamp': result_data["timestanmp"],
            'log_text': result_data["log"],
            'compressed_log': None,
            'test_result_json': json.dumps(result_data["testResult"], sort_keys=True)
        }

        db._test_results[test_name].append(result_record)
        saved_ids.append(result_id)

    print(f"✓ Saved {len(mock_test_results)} test results with IDs: {saved_ids}")

    # Show updated stats
    print(f"\nUpdated stats: {json.dumps(db.get_stats(), indent=2)}")

    # Example: Query test results
    print("\n3. Querying test results...")

    tx_power_results = db.load_test_results("TxPowerTest", limit=10)
    print(f"Found {len(tx_power_results)} TxPowerTest results:")
    for result in tx_power_results:
        print(f"  ID {result['id']}: {result['status']} at {result['timestamp']}")

    # Example: Get specific test result
    if saved_ids:
        specific_result = db.get_test_result_by_id("TxPowerTest", saved_ids[0])
        if specific_result:
            print(f"\nSpecific result (ID {saved_ids[0]}):")
            print(f"  Status: {specific_result['status']}")
            print(f"  Log: {specific_result['log_text'][:50]}...")

    # Example: Check integrity
    print("\n4. Checking data integrity...")
    integrity_issues = db.check_group_content_integrity()
    print(f"Integrity check: {len(integrity_issues)} issues found")

    # Example: Export all data
    print("\n5. Exporting data snapshot...")
    exported_data = db.export_data()
    print(f"Exported data contains {len(exported_data)} top-level keys")
    print(f"Plugin types: {list(exported_data.get('plugin_data', {}).keys())}")
    print(f"Test types: {list(exported_data.get('test_results', {}).keys())}")

    # Example: Cleanup old test results
    print("\n6. Testing cleanup...")
    deleted_count = db.cleanup_old_test_results("TxPowerTest", keep_count=1)
    print(f"Cleaned up {deleted_count} old test results")

    # Final stats
    print(f"\nFinal stats: {json.dumps(db.get_stats(), indent=2)}")

    # Close the database
    db.close()
    print("\n✓ Database closed")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    demo_inmemory_db()
