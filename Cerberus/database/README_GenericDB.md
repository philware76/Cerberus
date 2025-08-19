# GenericDB Parameter Persistence

## 1. Overview
GenericDB provides a **normalized, content‑addressed persistence layer** for plugin parameter groups used by Cerberus equipment, product, and test plugins. Its design goals:

- Avoid redundant storage of identical parameter group JSON blobs (global dedup by hash)
- Maintain a **version history** per (station, plugin_type, plugin_name, group_name) identity
- Fast no‑op when parameters are unchanged (hash comparison short‑circuit)
- Idempotent + race‑tolerant inserts that do **not waste AUTO_INCREMENT IDs** on duplicates
- Integrity + maintenance utilities (hash verification, legacy duplicate cleanup)

### Core Idea
Each logical parameter group (e.g. the "RF" group for a specific test plugin at a station) has:
- A stable identity row (`group_identity`)
- A pointer to its **current version** (`current_group_setting` → `group_settings` → `group_content`)
- A history of versions (`group_settings` rows – immutable mappings identity→content)
- A globally de‑duplicated JSON content row (`group_content`) shared by *any* identity whose canonical JSON matches

### Logical Flow (save_group)
```
Input values_map
  ↓ canonicalize JSON + SHA256
Compute group_hash
  ↓ fast read (joined) current hash
If identical → return (no writes)
  ↓ ensure identity (INSERT .. ON DUPLICATE KEY)
  ↓ ensure / reuse content row (SELECT first; INSERT if new; race-safe)
  ↓ does this identity already reference this content?
      Yes → conditionally ensure pointer (UPDATE-if-different / INSERT IGNORE) → return
      No  → INSERT (or reuse) new version row (ON DUPLICATE KEY for (identity,content))
            conditionally set pointer (UPDATE-if-different / INSERT IGNORE)
            commit
```

## 2. Schema
```
+------------------+        +------------------+        +-------------------+        +---------------------------+
|  group_identity  | 1    * |  group_settings  | *    1 |   group_content   |        |   current_group_setting   |
+------------------+        +------------------+        +-------------------+        +---------------------------+
| id (PK)          |<-------| group_identity_id|        | id (PK)           |        | group_identity_id (PK,FK) |
| station_id       |        | content_id (FK)--+------->| group_hash (UQ)   |        | setting_id (FK)           |
| plugin_type      |        | created_at       |        | group_json (JSON) |        | updated_at (ts auto)      |
| plugin_name      |        | (UQ gid,content) |        | created_at        |        +---------------------------+
| group_name       |        +------------------+        +-------------------+
| (UQ station,ptype,plugin,group)                                          
+------------------+
```

### Constraints & Indexes
| Table | Constraint / Index | Purpose |
|-------|--------------------|---------|
| group_identity | UNIQUE(station_id, plugin_type, plugin_name, group_name) | Stable identity lookup |
| group_content | UNIQUE(group_hash) | Global deduplication |
| group_settings | UNIQUE(group_identity_id, content_id) | Prevent duplicate historic rows under concurrency |
| current_group_setting | PK(group_identity_id) | O(1) pointer to current version |

## 3. Hashing & Canonical JSON
All JSON persisted in `group_content.group_json` is serialized with:
``json.dumps(obj, sort_keys=True, separators=(",", ":"))``
This ensures logically equivalent maps with different key order or whitespace yield identical `group_hash` (SHA256 of canonical string).

## 4. Detailed Operation (save_group)
| Step | SQL / Action | Why |
|------|--------------|-----|
| 1 | SELECT joined current hash | Cheap no‑op skip when unchanged |
| 2 | INSERT ... ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id) into `group_identity` | Create or fetch identity without touching row metadata |
| 3 | SELECT id FROM group_content WHERE group_hash=%s | Try reuse existing content row |
| 4 | INSERT INTO group_content VALUES ... (fallback) | Create new content blob; race handled by catching duplicate error |
| 5 | SELECT id FROM group_settings WHERE group_identity_id=? AND content_id=? | See if this version already exists for this identity |
| 6a (exists) | UPDATE current_group_setting ... WHERE setting_id<>?  + INSERT IGNORE | Pointer maintenance only when needed (no timestamp churn) |
| 6b (new) | INSERT ... ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id) into group_settings | Reuse existing version if concurrent thread inserted same pair |
| 7 | UPDATE then INSERT IGNORE for pointer | Same conditional pointer pattern |
| 8 | COMMIT | Atomic write set |

## 5. Integrity Utilities
### 5.1 `checkGroupContentIntegrity()`
Recomputes canonical JSON + SHA256 for every `group_content` row. Returns list of mismatches `(id, stored_hash, recomputed_hash)` and logs a WARNING if any found.
Use when auditing for corruption or manual DB edits.

### 5.2 `cleanup_duplicate_group_settings(dry_run=False)`
Legacy duplicate `(group_identity_id, content_id)` rows (possible before UNIQUE constraint) are detected and optionally removed.
Algorithm:
1. Aggregate duplicates (COUNT>1)
2. Pick smallest `id` = keep_id
3. Repoint `current_group_setting` rows referencing non‑kept IDs
4. Delete non‑kept rows (unless `dry_run=True`)
Returns a JSON‑like report with counts and per‑duplicate detail.

Run with `dry_run=True` first.

## 6. Concurrency & Idempotence
- Identity creation uses MySQL's LAST_INSERT_ID trick to return the existing PK without modifying the row.
- Content insertion first probes by hash; on race duplicate, SELECT after catching `ER_DUP_ENTRY` recovers the existing id.
- Historical version insertion uses UNIQUE(gid, content_id) to prevent duplicate rows; repeated inserts for same pair reuse `LAST_INSERT_ID(id)`.
- Pointer updates are conditional (UPDATE only if different) to avoid unnecessary row version changes & timestamp updates.
- Early hash short‑circuit eliminates *all* writes when values are the same, reducing contention.

Isolation: Default InnoDB (likely REPEATABLE READ). Logic is race‑tolerant under that and READ COMMITTED.

## 7. AUTO_INCREMENT Gap Minimization
- Avoids ON DUPLICATE for content rows (probe first) → fewer wasted ids.
- Reuses existing group_settings rows via UNIQUE constraint → no duplicate version rows for same content.
Gaps can still occur (failed inserts, rollback, unrelated tables) and are acceptable.

## 8. Migration Notes
If upgrading from older schema:
1. Run `cleanup_duplicate_group_settings(dry_run=True)` to see duplicates.
2. Run it with `dry_run=False` to normalize.
3. Ensure UNIQUE key exists: `SHOW INDEX FROM group_settings WHERE Key_name='uq_gid_content';`
4. If missing and no duplicates, add: `ALTER TABLE group_settings ADD UNIQUE KEY uq_gid_content (group_identity_id, content_id);`

## 9. Example Usage
```python
from Cerberus.database.genericDB import GenericDB
from Cerberus.common import DBInfo

# Connect
info = DBInfo(host='localhost', port=3306, username='user', password='pw', database='cerberus')
db = GenericDB('STATION_A', info)

# Save a plugin's groups
for plugin in equipment_plugins:
    db.save_plugin('equipment', plugin)

# Load persisted values back into a plugin instance
for plugin in equipment_plugins:
    db.load_equipment_into(plugin)

# Integrity check
bad = db.checkGroupContentIntegrity()
if bad:
    print('Corruption detected:', bad)

# Duplicate cleanup (dry run)
report = db.cleanup_duplicate_group_settings(dry_run=True)
print(report)
```

## 10. Query Snippets (Diagnostics)
Latest setting per identity with JSON:
```sql
SELECT gi.station_id, gi.plugin_type, gi.plugin_name, gi.group_name,
       gc.group_hash, gc.group_json, gs.id AS setting_id
FROM group_identity gi
JOIN current_group_setting cgs ON gi.id = cgs.group_identity_id
JOIN group_settings gs ON cgs.setting_id = gs.id
JOIN group_content gc ON gs.content_id = gc.id
ORDER BY gi.station_id, gi.plugin_type, gi.plugin_name, gi.group_name;
```
Historical versions for an identity:
```sql
SELECT gs.id, gc.group_hash, gc.created_at, gs.created_at
FROM group_identity gi
JOIN group_settings gs ON gi.id = gs.group_identity_id
JOIN group_content gc ON gs.content_id = gc.id
WHERE gi.station_id=? AND gi.plugin_type=? AND gi.plugin_name=? AND gi.group_name=?
ORDER BY gs.id;
```

## 11. Error Handling & Transactions
- Each `save_group` call uses a single implicit transaction; on MySQL error we attempt `rollback()`.
- Integrity & cleanup helpers perform controlled multi‑step operations; cleanup wraps mutations in an explicit transaction (manual `START TRANSACTION`) to ensure atomicity.

## 12. Potential Enhancements
| Idea | Benefit |
|------|---------|
| Add per‑identity version number column | Human friendly ordering independent of AUTO_INCREMENT |
| Add soft delete flag instead of physical delete | Auditing / recovery |
| Optional compression of large JSON blobs | Reduce storage if groups become large |
| Background job to prune old versions | Control history growth |
| Metrics counters (writes skipped, versions created) | Observability |

## 13. Edge Cases Considered
- Malformed JSON row → integrity check returns `<unparseable>` mismatch entry.
- Concurrent identical save → single version row due to UNIQUE(gid, content_id).
- Reverting to a *previous* content hash → version row reused (no new history row) and pointer adjusted.
- Non‑serializable parameter values → coerced to `str()` before persistence.

## 14. Glossary
| Term | Meaning |
|------|---------|
| Identity | Unique station + plugin_type + plugin_name + group_name |
| Content | Canonical JSON + hash representing parameter values |
| Version | Mapping of identity to content at a point in time (group_settings row) |
| Pointer | Current version reference for an identity (current_group_setting) |

---
Maintained by GenericDB. For questions or extension proposals, update this document alongside code changes to keep architecture knowledge synchronized.
