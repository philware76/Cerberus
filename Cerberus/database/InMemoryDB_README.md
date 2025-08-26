# InMemoryDB Implementation

## Overview

The `InMemoryDB` class is a complete in-memory implementation of the `BaseDB` abstract interface. It provides all the functionality of the Cerberus database system without requiring any external database infrastructure.

## Key Features

- **Zero Dependencies**: No database server required
- **Fast Operations**: All data stored in Python dictionaries and lists
- **Perfect for Testing**: Ideal for unit tests and integration tests
- **Full API Compatibility**: Implements all `BaseDB` methods
- **Data Compression**: Automatically compresses large log files
- **Rich Debugging**: Built-in statistics and data export capabilities
- **Thread-Safe**: Safe for single-threaded applications (not thread-safe across multiple threads)

## When to Use InMemoryDB

✅ **Perfect For:**
- Unit testing and integration testing
- Development and debugging
- Temporary data storage scenarios
- Proof of concept implementations
- CI/CD pipelines where database setup is impractical
- Quick prototyping

❌ **Not Suitable For:**
- Production environments requiring data persistence
- Multi-process applications sharing data
- Very large datasets (limited by available RAM)
- Applications requiring ACID transactions

## Usage Examples

### Basic Usage

```python
from Cerberus.database.inMemoryDB import InMemoryDB

# Create database instance
db = InMemoryDB("test_station")

# Save plugin configuration
db.save_plugin("equipment", my_equipment_plugin)

# Load plugin configuration
db.load_plugin_into("equipment", my_equipment_plugin)

# Save test results
result_id = db.save_test_result(my_test_result)

# Query test results
results = db.load_test_results("MyTest", limit=10)

# Clean up when done
db.close()
```

### Testing Example

```python
import unittest
from Cerberus.database.inMemoryDB import InMemoryDB

class MyTestCase(unittest.TestCase):
    def setUp(self):
        self.db = InMemoryDB("test_station")
    
    def tearDown(self):
        self.db.close()
    
    def test_plugin_save_load(self):
        # Test plugin persistence
        self.db.save_plugin("equipment", my_plugin)
        
        # Verify data was saved
        stats = self.db.get_stats()
        self.assertEqual(stats["total_plugins"], 1)
        
        # Test loading
        new_plugin = create_empty_plugin()
        self.db.load_plugin_into("equipment", new_plugin)
        # Assert plugin was loaded correctly...
```

### Development/Debugging

```python
# Create database for development
db = InMemoryDB("dev_station")

# Add some test data
db.save_plugin("equipment", spectrum_analyzer)
db.save_test_result(test_result)

# Get insights into stored data
stats = db.get_stats()
print(f"Stored {stats['total_plugins']} plugins and {stats['total_test_results']} test results")

# Export all data for inspection
data_snapshot = db.export_data()
with open("debug_snapshot.json", "w") as f:
    json.dump(data_snapshot, f, indent=2, default=str)
```

## API Reference

### Core Methods

| Method | Description |
|--------|-------------|
| `save_plugin(plugin_type, plugin)` | Save a plugin's configuration |
| `load_plugin_into(plugin_type, plugin)` | Load configuration into a plugin |
| `save_test_result(test_result)` | Save a test result, returns result ID |
| `load_test_results(test_name, limit, offset)` | Query test results with pagination |
| `delete_plugin(plugin_type, plugin_name)` | Delete all data for a plugin |
| `close()` | Clean up resources (clears all data) |

### Bulk Operations

| Method | Description |
|--------|-------------|
| `save_equipment(plugins)` | Save multiple equipment plugins |
| `save_tests(plugins)` | Save multiple test plugins |
| `save_products(plugins)` | Save multiple product plugins |

### Maintenance

| Method | Description |
|--------|-------------|
| `check_group_content_integrity()` | Verify data integrity |
| `cleanup_old_test_results(test_name, keep_count)` | Remove old test results |
| `wipe_db()` | Clear all data (dangerous!) |

### InMemoryDB-Specific Methods

| Method | Description |
|--------|-------------|
| `get_stats()` | Get statistics about stored data |
| `export_data()` | Export all data as JSON-serializable dict |

## Performance Characteristics

- **Memory Usage**: Proportional to stored data size
- **Operation Speed**: O(1) for most operations, O(n) for searches
- **Scalability**: Limited by available RAM
- **Startup Time**: Instant (no connection setup)

## Data Persistence

⚠️ **Important**: All data is lost when the InMemoryDB instance is destroyed or the application shuts down. This is by design for testing scenarios.

If you need persistence:
- Use `export_data()` to create snapshots
- Consider using `FileDB` for lightweight persistence
- Use `MySqlDB` or `PostgreSqlDB` for production scenarios

## Thread Safety

InMemoryDB is **not thread-safe**. If you need to use it in a multi-threaded environment, you must provide your own synchronization:

```python
import threading

class ThreadSafeInMemoryDB(InMemoryDB):
    def __init__(self, station_id):
        super().__init__(station_id)
        self._lock = threading.RLock()
    
    def save_plugin(self, plugin_type, plugin):
        with self._lock:
            super().save_plugin(plugin_type, plugin)
    
    # Add locks to other methods as needed...
```

## Best Practices

1. **Always call `close()`** in cleanup code or use context managers
2. **Use `get_stats()`** to monitor memory usage during development
3. **Export data snapshots** for debugging complex test scenarios
4. **Keep test data small** to ensure fast test execution
5. **Use meaningful station IDs** to distinguish different test scenarios
6. **Clear data between tests** using `wipe_db()` or creating new instances

## Migration from Other DB Types

Converting from other database implementations is straightforward:

```python
# Instead of this:
# db = MySqlDB("station", db_info)

# Use this:
db = InMemoryDB("station")

# All other code remains the same!
db.save_plugin("equipment", my_plugin)
results = db.load_test_results("MyTest")
```

## Integration with Test Frameworks

### pytest

```python
import pytest
from Cerberus.database.inMemoryDB import InMemoryDB

@pytest.fixture
def db():
    database = InMemoryDB("test_station")
    yield database
    database.close()

def test_something(db):
    # Use db fixture
    db.save_plugin("equipment", my_plugin)
    assert db.get_stats()["total_plugins"] == 1
```

### unittest

```python
class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.db = InMemoryDB("test_station")
    
    def tearDown(self):
        self.db.close()
```

## Troubleshooting

### Common Issues

1. **Memory Usage Growing**: Use `get_stats()` to monitor and `cleanup_old_test_results()` to manage test result storage
2. **Data Not Persisting**: By design! Use `export_data()` for snapshots if needed
3. **Import Errors**: Ensure `Cerberus.database.inMemoryDB` is in your Python path

### Debugging Tips

```python
# Check what's stored
stats = db.get_stats()
print(f"Data summary: {stats}")

# Export everything for inspection  
data = db.export_data()
print(f"Plugin types: {list(data['plugin_data'].keys())}")
print(f"Test types: {list(data['test_results'].keys())}")

# Verify data integrity
issues = db.check_group_content_integrity()
if issues:
    print(f"Found {len(issues)} integrity issues")
```
