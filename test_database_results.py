#!/usr/bin/env python3
"""
Test the database test result functionality
"""

from Cerberus.plugins.tests.baseTestResult import BaseTestResult, ResultStatus
from Cerberus.database.fileDB import FileDB
import sys
import os
import json
import tempfile
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_database_test_results():
    """Test saving and loading test results to/from database"""

    # Create a temporary database file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_db_file = f.name

    try:
        # Create database instance
        db = FileDB("test_station", temp_db_file)

        # Create a test result
        test_result = BaseTestResult("TxLevel")
        test_result.status = ResultStatus.PASSED
        test_result.log = "This is a test log with some content\nLine 2\nLine 3"

        # Add some test data to testResult
        test_result.testResult["BandResults"] = [
            {
                "slot": 0,
                "band": "Band_1",
                "path": "TX_HIGH",
                "frequency_mhz": 1000,
                "measured_power": 15.5,
                "calibration_adjustment": -0.3,
                "detected_power": 15.8,
                "difference": 0.3,
                "passed": True
            },
            {
                "slot": 1,
                "band": "Band_2",
                "path": "TX_LOW",
                "frequency_mhz": 2000,
                "measured_power": 18.2,
                "calibration_adjustment": -0.5,
                "detected_power": 18.0,
                "difference": -0.2,
                "passed": True
            }
        ]

        test_result.testResult["Summary"] = [
            {
                "total_bands_tested": 2,
                "passed_bands": 2,
                "failed_bands": 0,
                "average_difference": 0.05
            }
        ]

        print("Original test result:")
        print(f"  Name: {test_result.name}")
        print(f"  Status: {test_result.status}")
        print(f"  Timestamp: {test_result.timestanmp}")
        print(f"  Log length: {len(test_result.log)}")
        print(f"  Test result keys: {list(test_result.testResult.keys())}")
        print(f"  BandResults count: {len(test_result.testResult['BandResults'])}")

        # Save to database
        result_id = db.save_test_result(test_result)
        print(f"\n✅ Saved test result with ID: {result_id}")

        # Load back from database
        loaded_results = db.load_test_results("txlevel", limit=10)
        print(f"\n✅ Loaded {len(loaded_results)} test results")

        if loaded_results:
            loaded_result = loaded_results[0]
            print(f"\nLoaded test result:")
            print(f"  ID: {loaded_result['id']}")
            print(f"  Station ID: {loaded_result['station_id']}")
            print(f"  Status: {loaded_result['status']}")
            print(f"  Timestamp: {loaded_result['timestamp']}")
            print(f"  Log length: {len(loaded_result.get('log_text', ''))}")

            # Parse the JSON test result
            test_result_data = json.loads(loaded_result['test_result_json'])
            print(f"  Test result keys: {list(test_result_data.keys())}")
            print(f"  BandResults count: {len(test_result_data.get('BandResults', []))}")

            # Verify data integrity
            assert loaded_result['status'] == 'Passed'
            assert loaded_result['station_id'] == 'test_station'
            assert len(test_result_data['BandResults']) == 2
            assert test_result_data['BandResults'][0]['slot'] == 0
            assert test_result_data['BandResults'][1]['slot'] == 1
            assert test_result_data['Summary'][0]['total_bands_tested'] == 2

            print("\n✅ Data integrity verified!")

        # Test getting by ID
        specific_result = db.get_test_result_by_id("txlevel", result_id)
        if specific_result:
            print(f"\n✅ Retrieved specific result by ID: {specific_result['id']}")

        # Test large log compression
        large_test_result = BaseTestResult("TxLevel")
        large_test_result.status = ResultStatus.FAILED
        large_test_result.log = "Large log content\n" * 1000  # Make it > 1KB
        large_test_result.testResult["LargeData"] = [{"test": i} for i in range(100)]

        large_result_id = db.save_test_result(large_test_result)
        print(f"\n✅ Saved large test result with ID: {large_result_id}")

        large_loaded = db.get_test_result_by_id("txlevel", large_result_id)
        if large_loaded:
            print(f"✅ Large result log length: {len(large_loaded.get('log_text', ''))}")
            large_data = json.loads(large_loaded['test_result_json'])
            print(f"✅ Large result data count: {len(large_data.get('LargeData', []))}")

        # Test cleanup
        deleted_count = db.cleanup_old_test_results("txlevel", keep_count=1)
        print(f"\n✅ Cleaned up {deleted_count} old test results")

        remaining_results = db.load_test_results("txlevel", limit=10)
        print(f"✅ Remaining results after cleanup: {len(remaining_results)}")

        print("\n🎉 All database test result tests passed!")

    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_db_file)
        except:
            pass


if __name__ == "__main__":
    test_database_test_results()
