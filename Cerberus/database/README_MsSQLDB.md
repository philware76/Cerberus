# Microsoft SQL Server Database Backend

This module provides a Microsoft SQL Server implementation of the Cerberus database backend, following the same API as the MySQL implementation.

## Overview

The `MsSqlDB` class inherits from `CerberusDB` and provides SQL Server-specific implementations for:

- Plugin parameter group persistence
- Test result storage and retrieval
- Database schema management
- Integrity checking and maintenance

## Features

### Normalized Schema
- **group_identity**: Unique identifiers per station/plugin/group
- **group_content**: Global deduplication of JSON content by hash
- **group_settings**: Historical immutable versions
- **current_group_setting**: Pointers to latest versions
- **test_results**: Test execution results with compression support

### SQL Server Specific Features
- Uses `IDENTITY` columns for auto-increment
- `NVARCHAR(MAX)` for JSON storage
- `DATETIME2` for timestamps with better precision
- `MERGE` statements for upsert operations
- `STRING_AGG` for duplicate detection
- `OFFSET/FETCH` for pagination
- Proper transaction handling with rollback safety

## Dependencies

```bash
pip install pyodbc
```

## Usage

```python
from Cerberus.common import DBInfo
from Cerberus.database.msSQLDB import MsSqlDB

# Configure database connection
db_info = DBInfo(
    host="your-sql-server.com",
    port=1433,
    database="cerberus_db", 
    username="your_username",
    password="your_password"
)

# Create database instance
db = MsSqlDB("station_001", db_info)

# Use the same API as MySQL implementation
db.save_plugin("equipment", my_plugin)
db.load_plugin_into("equipment", my_plugin)

# Test results
db.save_test_result(test_result)
results = db.load_test_results("MyTest", limit=50)

# Cleanup
db.close()
```

## Connection String

The implementation uses an ODBC connection string with these features:
- **Driver**: ODBC Driver 17 for SQL Server
- **Encryption**: Enabled by default
- **Timeouts**: 10s connection, 30s command
- **Trust**: Server certificate validation enabled

## Error Handling

SQL Server specific error detection for:
- Login failures
- Database access issues  
- Network connectivity problems
- Connection timeouts

## Schema Differences from MySQL

| Feature | MySQL | SQL Server |
|---------|-------|------------|
| Auto-increment | `AUTO_INCREMENT` | `IDENTITY(1,1)` |
| JSON storage | `JSON` | `NVARCHAR(MAX)` |
| Timestamps | `TIMESTAMP` | `DATETIME2` |
| String aggregation | `GROUP_CONCAT` | `STRING_AGG` |
| Upsert | `ON DUPLICATE KEY UPDATE` | `MERGE` |
| Pagination | `LIMIT/OFFSET` | `OFFSET/FETCH` |
| Last insert ID | `LAST_INSERT_ID()` | `@@IDENTITY` |

## Maintenance Operations

Same maintenance operations as MySQL:
- `checkGroupContentIntegrity()`: Verify hash consistency
- `cleanup_duplicate_group_settings()`: Remove duplicate historical versions
- `cleanup_old_test_results()`: Manage test result retention
- `wipe_db()`: Complete database reset (destructive)

## Testing

Basic structure validation:
```bash
python test_mssql_structure.py
```

For full integration testing, ensure you have:
1. SQL Server instance running
2. Database created
3. User with appropriate permissions
4. ODBC Driver 17 for SQL Server installed

## Compatibility

- **SQL Server**: 2016 or later (for `STRING_AGG` support)
- **Python**: 3.8+
- **ODBC Driver**: 17 or later recommended
