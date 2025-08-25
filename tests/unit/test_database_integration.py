"""
Integration test for test result database functionality
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add the project root to Python path for direct execution
if __name__ == '__main__':
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Cerberus.database.fileDB import FileDB
from Cerberus.executor import Executor
from Cerberus.manager import PluginService
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.plugins.tests.baseTestResult import BaseTestResult, ResultStatus


class MockDatabase(FileDB):
    """Mock database for testing that tracks calls"""

    def __init__(self):
        # Don't call super().__init__ to avoid file operations
        self.station_id = "test_station"
        self.saved_results = []
        self.call_count = 0

    def save_test_result(self, test_result):
        self.call_count += 1
        result_record = {
            "id": self.call_count,
            "name": test_result.name,
            "status": test_result.status.value if hasattr(test_result.status, 'value') else str(test_result.status),
            "timestamp": test_result.timestanmp,
            "log": test_result.log,
            "test_result_json": json.dumps(test_result.testResult, default=str)
        }
        self.saved_results.append(result_record)
        return self.call_count


class MockTest(BaseTest):
    """Mock test for testing"""

    def __init__(self, name="MockTest"):
        super().__init__(name, checkProduct=False)
        self.run_called = False

    def run(self):
        super().run()
        self.run_called = True

        # Simulate some test results
        self.result.status = ResultStatus.PASSED
        self.result.testResult["MockResults"] = [
            {"measurement": 1, "value": 10.5},
            {"measurement": 2, "value": 11.2}
        ]


class TestDatabaseIntegration(unittest.TestCase):
    """Test the complete database integration for test results"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_plugin_service = MagicMock(spec=PluginService)
        self.mock_database = MockDatabase()
        self.mock_plugin_service.database = self.mock_database

        self.executor = Executor(self.mock_plugin_service)

    def test_executor_saves_test_result_to_database(self):
        """Test that executor saves test results to database after test completion"""
        # Create a mock test
        test = MockTest("TestSave")

        # Mock the required equipment preparation
        with patch.object(self.executor.required_equipment, 'prepare', return_value=True):
            # Run the test
            success = self.executor.runTest(test, product=None)

        # Verify test ran successfully
        self.assertTrue(success)
        self.assertTrue(test.run_called)

        # Verify test result was saved to database
        self.assertEqual(self.mock_database.call_count, 1)
        self.assertEqual(len(self.mock_database.saved_results), 1)

        saved_result = self.mock_database.saved_results[0]
        self.assertEqual(saved_result["name"], "TestSave")
        self.assertEqual(saved_result["status"], "Passed")

        # Verify test result data was saved
        result_data = json.loads(saved_result["test_result_json"])
        self.assertIn("MockResults", result_data)
        self.assertEqual(len(result_data["MockResults"]), 2)
        self.assertEqual(result_data["MockResults"][0]["measurement"], 1)

    def test_executor_handles_database_save_failure_gracefully(self):
        """Test that test execution continues even if database save fails"""
        # Make database save fail
        self.mock_database.save_test_result = MagicMock(side_effect=Exception("Database error"))

        test = MockTest("TestFailure")

        with patch.object(self.executor.required_equipment, 'prepare', return_value=True):
            # Should not raise exception despite database failure
            success = self.executor.runTest(test, product=None)

        # Test should still succeed
        self.assertTrue(success)
        self.assertTrue(test.run_called)

        # Database save should have been attempted
        self.mock_database.save_test_result.assert_called_once()

    def test_executor_skips_database_save_when_no_database(self):
        """Test that executor doesn't fail when no database is available"""
        # Remove database from plugin service
        self.mock_plugin_service.database = None

        test = MockTest("TestNoDatabase")

        with patch.object(self.executor.required_equipment, 'prepare', return_value=True):
            success = self.executor.runTest(test, product=None)

        # Test should still succeed
        self.assertTrue(success)
        self.assertTrue(test.run_called)

    def test_executor_handles_test_with_no_result(self):
        """Test that executor handles tests that don't produce results"""
        test = MockTest("TestNoResult")

        # Override the run method to clear the result
        def run_no_result():
            BaseTest.run(test)  # Call base implementation
            # Use setattr to bypass type checking
            setattr(test, 'result', None)

        test.run = run_no_result

        with patch.object(self.executor.required_equipment, 'prepare', return_value=True):
            success = self.executor.runTest(test, product=None)

        # Should return False for no results
        self.assertFalse(success)

        # No database save should be attempted
        self.assertEqual(self.mock_database.call_count, 0)


class TestFileDBTestResults(unittest.TestCase):
    """Test FileDB test result functionality"""

    def setUp(self):
        """Set up test database"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_file.close()
        self.db = FileDB("test_station", self.temp_file.name)

    def tearDown(self):
        """Clean up test database"""
        try:
            os.unlink(self.temp_file.name)
        except:
            pass

    def test_save_and_load_test_result(self):
        """Test basic save and load functionality"""
        # Create test result
        result = BaseTestResult("TestSaveLoad", ResultStatus.PASSED)
        result.log = "Test log content"
        result.testResult = {"test_data": [1, 2, 3]}

        # Save to database
        result_id = self.db.save_test_result(result)
        self.assertIsInstance(result_id, int)
        self.assertGreater(result_id, 0)

        # Load from database
        loaded_results = self.db.load_test_results("testsaveload", limit=1)
        self.assertEqual(len(loaded_results), 1)

        loaded = loaded_results[0]
        self.assertEqual(loaded["id"], result_id)
        self.assertEqual(loaded["status"], "Passed")
        self.assertEqual(loaded["log_text"], "Test log content")

        # Verify JSON data
        test_data = json.loads(loaded["test_result_json"])
        self.assertEqual(test_data["test_data"], [1, 2, 3])

    def test_compression_for_large_logs(self):
        """Test that large logs are compressed"""
        # Create result with large log
        result = BaseTestResult("TestCompression", ResultStatus.FAILED)
        result.log = "Large log content\n" * 500  # > 1KB
        result.testResult = {"data": "test"}

        # Save to database
        result_id = self.db.save_test_result(result)

        # Load back
        loaded = self.db.get_test_result_by_id("testcompression", result_id)
        self.assertIsNotNone(loaded)

        # Log should be decompressed correctly
        if loaded is not None:
            self.assertEqual(len(loaded["log_text"]), len(result.log))
            self.assertTrue(loaded["log_text"].startswith("Large log content"))

    def test_cleanup_old_results(self):
        """Test cleanup of old test results"""
        # Create multiple test results
        for i in range(5):
            result = BaseTestResult("TestCleanup", ResultStatus.PASSED)
            result.testResult = {"run": i}
            self.db.save_test_result(result)

        # Verify all were saved
        results = self.db.load_test_results("testcleanup", limit=10)
        self.assertEqual(len(results), 5)

        # Cleanup keeping only 2
        deleted = self.db.cleanup_old_test_results("testcleanup", keep_count=2)
        self.assertEqual(deleted, 3)

        # Verify only 2 remain
        remaining = self.db.load_test_results("testcleanup", limit=10)
        self.assertEqual(len(remaining), 2)

    def test_delete_specific_result(self):
        """Test deletion of specific test result"""
        result = BaseTestResult("TestDelete", ResultStatus.PASSED)
        result_id = self.db.save_test_result(result)

        # Verify it exists
        loaded = self.db.get_test_result_by_id("testdelete", result_id)
        self.assertIsNotNone(loaded)

        # Delete it
        deleted = self.db.delete_test_result("testdelete", result_id)
        self.assertTrue(deleted)

        # Verify it's gone
        loaded = self.db.get_test_result_by_id("testdelete", result_id)
        self.assertIsNone(loaded)

        # Try to delete again (should return False)
        deleted_again = self.db.delete_test_result("testdelete", result_id)
        self.assertFalse(deleted_again)


if __name__ == '__main__':
    unittest.main()
