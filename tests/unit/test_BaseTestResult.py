"""
Unit tests for BaseTestResult class
"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import patch

# Add the project root to Python path for direct execution
if __name__ == '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Cerberus.plugins.tests.baseTestResult import BaseTestResult, ResultStatus


class TestBaseTestResult(unittest.TestCase):
    """Test cases for BaseTestResult class"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.result = BaseTestResult("TestResult")

    def test_init_default(self):
        """Test BaseTestResult initialization with default parameters"""
        result = BaseTestResult("TestName")

        self.assertEqual(result.name, "TestName")
        self.assertIsInstance(result.timestanmp, datetime)
        self.assertEqual(result.log, "")
        self.assertEqual(result.testReferences, {"Equipment": [], "Test": []})
        self.assertEqual(result.testResult, {})

    def test_init_with_status(self):
        """Test BaseTestResult initialization with status parameter"""
        result = BaseTestResult("TestName", ResultStatus.PASSED)

        # Note: There's a bug in the original code - it sets PENDING regardless of the input
        # This test documents the current behavior
        self.assertEqual(result.status, ResultStatus.PENDING)

    def test_addTestResult_single_item(self):
        """Test adding a single test result"""
        test_data = {
            "slot": 0,
            "band": "Test Band",
            "frequency_mhz": 1000,
            "measured_power": 15.5
        }

        self.result.addTestResult("BandResults", test_data)

        self.assertIn("BandResults", self.result.testResult)
        self.assertEqual(len(self.result.testResult["BandResults"]), 1)
        self.assertEqual(self.result.testResult["BandResults"][0], test_data)

    def test_addTestResult_multiple_items_same_category(self):
        """Test adding multiple test results to the same category"""
        test_data_1 = {
            "slot": 0,
            "band": "Test Band 1",
            "frequency_mhz": 1000,
            "measured_power": 15.5
        }

        test_data_2 = {
            "slot": 1,
            "band": "Test Band 2",
            "frequency_mhz": 2000,
            "measured_power": 18.2
        }

        self.result.addTestResult("BandResults", test_data_1)
        self.result.addTestResult("BandResults", test_data_2)

        self.assertIn("BandResults", self.result.testResult)
        self.assertEqual(len(self.result.testResult["BandResults"]), 2)
        self.assertEqual(self.result.testResult["BandResults"][0], test_data_1)
        self.assertEqual(self.result.testResult["BandResults"][1], test_data_2)

    def test_addTestResult_multiple_categories(self):
        """Test adding test results to different categories"""
        band_data = {
            "slot": 0,
            "band": "Test Band",
            "frequency_mhz": 1000,
            "measured_power": 15.5
        }

        summary_data = {
            "total_bands_tested": 1,
            "passed": 1,
            "failed": 0
        }

        self.result.addTestResult("BandResults", band_data)
        self.result.addTestResult("Summary", summary_data)

        self.assertIn("BandResults", self.result.testResult)
        self.assertIn("Summary", self.result.testResult)
        self.assertEqual(len(self.result.testResult["BandResults"]), 1)
        self.assertEqual(len(self.result.testResult["Summary"]), 1)
        self.assertEqual(self.result.testResult["BandResults"][0], band_data)
        self.assertEqual(self.result.testResult["Summary"][0], summary_data)

    def test_addTestResult_various_data_types(self):
        """Test adding various data types as test results"""
        # Dictionary
        dict_data = {"key": "value"}
        self.result.addTestResult("DictData", dict_data)

        # List
        list_data = [1, 2, 3, 4]
        self.result.addTestResult("ListData", list_data)

        # String
        string_data = "test string"
        self.result.addTestResult("StringData", string_data)

        # Number
        number_data = 42.5
        self.result.addTestResult("NumberData", number_data)

        # Boolean
        bool_data = True
        self.result.addTestResult("BoolData", bool_data)

        # Verify all data types are stored correctly
        self.assertEqual(self.result.testResult["DictData"][0], dict_data)
        self.assertEqual(self.result.testResult["ListData"][0], list_data)
        self.assertEqual(self.result.testResult["StringData"][0], string_data)
        self.assertEqual(self.result.testResult["NumberData"][0], number_data)
        self.assertEqual(self.result.testResult["BoolData"][0], bool_data)

    @patch('Cerberus.plugins.tests.baseTestResult.logger')
    def test_addTestResult_logging(self, mock_logger):
        """Test that addTestResult logs correctly"""
        test_data = {"test": "data"}

        self.result.addTestResult("TestCategory", test_data)

        mock_logger.debug.assert_called_once_with("Added 'TestCategory' to TestResult result list")

    def test_addTestResult_empty_string_category(self):
        """Test adding test result with empty string category name"""
        test_data = {"test": "data"}

        self.result.addTestResult("", test_data)

        self.assertIn("", self.result.testResult)
        self.assertEqual(len(self.result.testResult[""]), 1)
        self.assertEqual(self.result.testResult[""][0], test_data)

    def test_addTestResult_none_data(self):
        """Test adding None as test result data"""
        self.result.addTestResult("NoneData", None)

        self.assertIn("NoneData", self.result.testResult)
        self.assertEqual(len(self.result.testResult["NoneData"]), 1)
        self.assertIsNone(self.result.testResult["NoneData"][0])

    def test_result_status_enum_values(self):
        """Test that all expected ResultStatus enum values exist"""
        expected_statuses = [
            "PENDING", "PASSED", "FAILED", "SKIPPED",
            "WAIVED", "FLAGGED", "ERROR"
        ]

        for status_name in expected_statuses:
            self.assertTrue(hasattr(ResultStatus, status_name))

        # Test specific values
        self.assertEqual(ResultStatus.PENDING.value, "Pending")
        self.assertEqual(ResultStatus.PASSED.value, "Passed")
        self.assertEqual(ResultStatus.FAILED.value, "Failed")
        self.assertEqual(ResultStatus.SKIPPED.value, "Skipped")
        self.assertEqual(ResultStatus.WAIVED.value, "Waived")
        self.assertEqual(ResultStatus.FLAGGED.value, "Flaged")  # Note: intentional typo in original code
        self.assertEqual(ResultStatus.ERROR.value, "Error")


class TestTxLevelTestResultIntegration(unittest.TestCase):
    """Integration tests simulating how TxLevelTest would use BaseTestResult"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.result = BaseTestResult("TxLevelTest")

    def test_tx_level_test_workflow(self):
        """Test a typical TxLevelTest workflow with multiple band measurements"""
        # Simulate measurements from multiple bands
        band_measurements = [
            {
                "slot": 0,
                "band": "Band_1",
                "path": "TX_HIGH",
                "frequency_mhz": 1000,
                "measured_power": 15.5,
                "calibration_adjustment": -0.3,
                "detected_power": 15.8,
                "difference": 0.3
            },
            {
                "slot": 1,
                "band": "Band_2",
                "path": "TX_LOW",
                "frequency_mhz": 2000,
                "measured_power": 18.2,
                "calibration_adjustment": -0.5,
                "detected_power": 18.0,
                "difference": -0.2
            },
            {
                "slot": 2,
                "band": "Band_3",
                "path": "TX_HIGH",
                "frequency_mhz": 2500,
                "measured_power": 20.1,
                "calibration_adjustment": -0.1,
                "detected_power": 20.3,
                "difference": 0.2
            }
        ]

        # Add each measurement to results (simulating TxLevelTest.testBand())
        for measurement in band_measurements:
            self.result.addTestResult("BandResults", measurement)

        # Verify all measurements are stored
        self.assertIn("BandResults", self.result.testResult)
        self.assertEqual(len(self.result.testResult["BandResults"]), 3)

        # Verify specific measurement data
        stored_measurements = self.result.testResult["BandResults"]
        for i, expected_measurement in enumerate(band_measurements):
            self.assertEqual(stored_measurements[i], expected_measurement)

        # Test that we can retrieve specific measurements
        band_1_measurement = stored_measurements[0]
        self.assertEqual(band_1_measurement["slot"], 0)
        self.assertEqual(band_1_measurement["band"], "Band_1")
        self.assertEqual(band_1_measurement["frequency_mhz"], 1000)
        self.assertAlmostEqual(band_1_measurement["measured_power"], 15.5)

        # Add a test summary
        test_summary = {
            "total_bands_tested": len(band_measurements),
            "average_difference": sum(m["difference"] for m in band_measurements) / len(band_measurements),
            "max_difference": max(m["difference"] for m in band_measurements),
            "min_difference": min(m["difference"] for m in band_measurements)
        }

        self.result.addTestResult("Summary", test_summary)

        # Verify summary is stored correctly
        self.assertIn("Summary", self.result.testResult)
        self.assertEqual(len(self.result.testResult["Summary"]), 1)

        summary = self.result.testResult["Summary"][0]
        self.assertEqual(summary["total_bands_tested"], 3)
        self.assertAlmostEqual(summary["average_difference"], 0.1, places=2)
        self.assertEqual(summary["max_difference"], 0.3)
        self.assertEqual(summary["min_difference"], -0.2)


if __name__ == '__main__':
    unittest.main()
