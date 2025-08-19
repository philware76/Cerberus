import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Iterable, cast

import mysql.connector
from mysql.connector import errorcode

from Cerberus.common import DBInfo
from Cerberus.database.baseDB import BaseDB
from Cerberus.logConfig import getLogger
from Cerberus.plugins.baseParameters import BaseParameter
from Cerberus.plugins.basePlugin import BasePlugin

logger = getLogger("Database")
logger.setLevel(logging.INFO)


@dataclass
class SettingRecord:
    id: int
    station_id: str
    plugin_type: str  # 'equipment' | 'product' | 'test'
    plugin_name: str
    group_name: str
    group_json: str
    param_hash: str

    def key(self) -> tuple[str, str, str, str]:
        return (self.station_id, self.plugin_type, self.plugin_name, self.group_name)


class GenericDB(BaseDB):
    """Generic persistence for plugin parameter settings.
    """

    def __init__(self, station_id: str, dbInfo: DBInfo):
        self.station_id = station_id
        self.db_info = dbInfo
        self.conn = mysql.connector.connect(
            host=dbInfo.host,
            port=dbInfo.port,
            user=dbInfo.username,
            password=dbInfo.password,
            database=dbInfo.database
        )
        self._ensure_tables()

        invalidContent = self.checkGroupContentIntegrity()
        if len(invalidContent) > 0:
            logger.error("Database integrity: Broken!")
            logger.error("Group Content is invalid on these entries:")
            for id, badHash, goodHash in invalidContent:
                logger.error(f"ID:{id}: {badHash} should be: {goodHash}")
        else:
            logger.info("Database integrity: OK")

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    # ------------------------------------------------------------------------------------------------------------
    def _ensure_tables(self):
        """Ensure normalized tables exist (fresh schema, no migration needed).

        Normalized schema:
          group_identity (unique per station/plugin/group)
          group_content  (unique JSON content canonicalized by hash; globally de-duplicated)
          group_settings (historical immutable versions referencing identity + content)
          current_group_setting (pointer to latest version per identity)
        """
        cur = self.conn.cursor()
        try:
            # Identity table (one row per unique group at a station)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_identity (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    station_id VARCHAR(100) NOT NULL,
                    plugin_type VARCHAR(32) NOT NULL,
                    plugin_name VARCHAR(128) NOT NULL,
                    group_name VARCHAR(128) NOT NULL,
                    UNIQUE KEY uq_group_identity (station_id, plugin_type, plugin_name, group_name)
                )
                """
            )

            # Global content table (one row per unique canonical JSON blob)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_content (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    group_hash CHAR(64) NOT NULL UNIQUE,
                    group_json JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Historical immutable versions mapping identity -> content
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_settings (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    group_identity_id BIGINT NOT NULL,
                    content_id BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_gid_content (group_identity_id, content_id),
                    KEY idx_gid_created (group_identity_id, id),
                    KEY idx_gid_content (group_identity_id, content_id),
                    CONSTRAINT fk_gs_identity FOREIGN KEY (group_identity_id)
                        REFERENCES group_identity(id) ON DELETE CASCADE,
                    CONSTRAINT fk_gs_content FOREIGN KEY (content_id)
                        REFERENCES group_content(id) ON DELETE RESTRICT
                )
                """
            )

            # In case table pre-existed without the UNIQUE key, attempt to add it (ignore if already there)
            try:  # pragma: no cover - migration path
                cur.execute("ALTER TABLE group_settings ADD UNIQUE KEY uq_gid_content (group_identity_id, content_id)")
            except Exception:
                pass

            # Pointer to current version
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS current_group_setting (
                    group_identity_id BIGINT PRIMARY KEY,
                    setting_id BIGINT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_setting_id (setting_id),
                    CONSTRAINT fk_cgs_identity FOREIGN KEY (group_identity_id)
                        REFERENCES group_identity(id) ON DELETE CASCADE,
                    CONSTRAINT fk_cgs_setting FOREIGN KEY (setting_id)
                        REFERENCES group_settings(id) ON DELETE CASCADE
                )
                """
            )

            self.conn.commit()
        finally:
            cur.close()

    # --------------------------------------------------------------------------------------------------------
    @staticmethod
    def _canonical_json(d: dict) -> str:
        """Return a deterministic JSON string for hashing (sorted keys, no spaces)."""
        return json.dumps(d, sort_keys=True, separators=(",", ":"))

    @classmethod
    def compute_param_hash(cls, param: BaseParameter) -> tuple[str, str]:
        """Compute the SHA256 hex digest for a parameter's JSON representation.

        Returns (hash_hex, canonical_json_string)
        """
        pdata = param.to_dict()
        canonical = cls._canonical_json(pdata)
        h = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return h, canonical

    @classmethod
    def compute_group_hash(cls, values_map: dict) -> tuple[str, str]:
        """Compute SHA256 hash and canonical JSON for a mapping of parameter_name -> value."""
        canonical = cls._canonical_json(values_map)
        h = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return h, canonical

    @staticmethod
    def _ensure_json_serializable(values: dict) -> dict:
        """Return a copy of values where any non-JSON-serializable values are converted to strings.

        This keeps persistence robust in case a plugin stores unusual Python objects as a value.
        """
        safe: dict = {}
        for k, v in values.items():
            try:
                # Try to serialize single value
                json.dumps(v)
                safe[k] = v
            except TypeError:
                # Fall back to string representation
                safe[k] = str(v)
        return safe

    @staticmethod
    def compute_hash_from_json(group_json: str) -> str:
        """Compute SHA256 hash for an arbitrary parameter JSON string.

        The JSON string will be parsed and re-serialized with canonical formatting so
        semantically equivalent inputs (ordering/whitespace differences) produce the
        same hash.
        """
        try:
            data = json.loads(group_json)
        except Exception:  # pragma: no cover - defensive
            # Hash raw string as fallback (should not normally happen if caller provides valid JSON)
            return hashlib.sha256(group_json.encode("utf-8")).hexdigest()
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------------------------------------------------
    def save_plugin(self, plugin_type: str, plugin: BasePlugin):
        # Persist an entire parameter group as a single JSON blob mapping parameter_name->value.
        for group_name, group in plugin._groupParams.items():  # noqa: SLF001 (internal access intentional)
            # build mapping of name -> value and ensure JSON serializable
            values = {pname: p.value for pname, p in group.items()}
            safe_values = self._ensure_json_serializable(values)
            self.save_group(plugin_type, plugin.name, group_name, safe_values)

    def save_group(self, plugin_type: str, plugin_name: str, group_name: str, values_map: dict) -> None:
        """
        Save an entire parameter group as a JSON mapping parameter_name->value.
        Global de-duplication: any identical JSON content (by canonical hash) is stored only once
        in group_content and reused across ANY plugin/group identity. Historical versions for an
        identity point to content rows; if the same content hash recurs for that identity we reuse
        the existing historical version (so we don't accumulate duplicates from toggling back and
        forth).
        """
        group_hash, canonical_json = self.compute_group_hash(values_map)
        # Fast path: attempt to read existing current hash and skip all writes if identical.
        read_cur = self.conn.cursor()
        try:
            read_cur.execute(
                """
                SELECT gc.group_hash
                FROM group_identity gi
                JOIN current_group_setting cgs ON gi.id = cgs.group_identity_id
                JOIN group_settings gs ON cgs.setting_id = gs.id
                JOIN group_content gc ON gs.content_id = gc.id
                WHERE gi.station_id=%s AND gi.plugin_type=%s AND gi.plugin_name=%s AND gi.group_name=%s
                LIMIT 1
                """,
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            row = read_cur.fetchone()
            if row:
                existing_hash = str(row[0])  # type: ignore[index]
                if existing_hash == group_hash:
                    logger.debug(
                        f"Group: '{group_name}' for plugin '{plugin_name}' unchanged (hash match); skipped DB writes. hash={group_hash}"
                    )
                    return
        finally:
            read_cur.close()

        cur = self.conn.cursor()
        try:
            # Resolve / create identity (LAST_INSERT_ID trick returns existing id on duplicate)
            cur.execute(
                """
                INSERT INTO group_identity (station_id, plugin_type, plugin_name, group_name)
                VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
                """,
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            gid = cur.lastrowid

            # Locate or insert global content row WITHOUT burning an AUTO_INCREMENT value when
            # the hash already exists. The prior ON DUPLICATE KEY pattern allocates and discards
            # ids on duplicates, creating large gaps. This SELECT -> INSERT approach reduces (but
            # cannot eliminate) gaps. A race where another session inserts the same hash between
            # our SELECT and INSERT is handled by catching ER_DUP_ENTRY and re-selecting.
            cur.execute("SELECT id FROM group_content WHERE group_hash=%s", (group_hash,))
            row = cur.fetchone()
            if row:
                content_id = int(row[0])  # type: ignore[index]
            else:
                try:
                    cur.execute(
                        "INSERT INTO group_content (group_hash, group_json) VALUES (%s,%s)",
                        (group_hash, canonical_json)
                    )
                    content_id = cur.lastrowid
                except mysql.connector.Error as e:  # pragma: no cover - race condition path
                    if getattr(e, "errno", None) == errorcode.ER_DUP_ENTRY:
                        # Another connection inserted concurrently; fetch the id now present.
                        cur.execute("SELECT id FROM group_content WHERE group_hash=%s", (group_hash,))
                        content_id = int(cur.fetchone()[0])  # type: ignore[index]
                    else:
                        raise

            # Does this identity already have a historical setting pointing to this content?
            cur.execute(
                """SELECT id FROM group_settings WHERE group_identity_id=%s AND content_id=%s LIMIT 1""",
                (gid, content_id)
            )
            existing_for_identity = cur.fetchone()

            if existing_for_identity is not None:
                setting_id = int(existing_for_identity[0])  # type: ignore[index,arg-type]
                # Only change current_group_setting if it is missing or points at a different setting.
                # 1. Try to update only when different (prevents bumping updated_at when unchanged)
                cur.execute(
                    """
                    UPDATE current_group_setting
                    SET setting_id=%s
                    WHERE group_identity_id=%s AND setting_id<>%s
                    """,
                    (setting_id, gid, setting_id)
                )
                if cur.rowcount == 0:
                    # Either the pointer already matches (no action needed) OR the row is absent.
                    # 2. Insert it if absent (IGNORE avoids error if it actually existed and matched).
                    cur.execute(
                        """
                        INSERT IGNORE INTO current_group_setting (group_identity_id, setting_id)
                        VALUES (%s,%s)
                        """,
                        (gid, setting_id)
                    )
                self.conn.commit()
                logger.debug(
                    f"Group: '{group_name}' for plugin '{plugin_name}' unchanged; reused existing setting_id={setting_id} (gid={gid}) hash={group_hash}."
                )
                return

            # Insert (or reuse existing) historical version referencing shared content.
            # UNIQUE (group_identity_id, content_id) ensures only one row per pair; the ON DUPLICATE clause
            # fetches existing id without creating a duplicate row.
            cur.execute(
                """
                INSERT INTO group_settings (group_identity_id, content_id) VALUES (%s,%s)
                ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
                """,
                (gid, content_id)
            )
            new_setting_id = cur.lastrowid

            # Point current_group_setting at the new/reused setting only if different or missing.
            cur.execute(
                """
                UPDATE current_group_setting
                SET setting_id=%s
                WHERE group_identity_id=%s AND setting_id<>%s
                """,
                (new_setting_id, gid, new_setting_id)
            )
            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT IGNORE INTO current_group_setting (group_identity_id, setting_id)
                    VALUES (%s,%s)
                    """,
                    (gid, new_setting_id)
                )

            self.conn.commit()
            logger.debug(
                f"Group: '{group_name}' for plugin '{plugin_name}' changed; created new setting_id={new_setting_id} (gid={gid}) hash={group_hash}."
            )

        except mysql.connector.Error as err:  # pragma: no cover - operational
            try:
                self.conn.rollback()
            except Exception:
                pass
            logger.error(f"Failed to save group {plugin_name}.{group_name}: {err}")

        finally:
            cur.close()

    def save_many(self, plugin_type: str, plugins: Iterable[BasePlugin]):
        for p in plugins:
            self.save_plugin(plugin_type, p)

    # ------------------------------------------------------------------------------------------------------------
    def load_plugin_into(self, plugin_type: str, plugin: BasePlugin):
        # Prefer group-level persisted entry (single JSON blob). Fall back to per-parameter rows
        # for compatibility with old data.
        for group_name, group in plugin._groupParams.items():  # noqa: SLF001
            # Try to load a group-level blob
            cur = self.conn.cursor(dictionary=True)
            try:
                cur.execute(
                    """
                    SELECT gc.group_json FROM group_identity gi
                    JOIN current_group_setting cgs ON gi.id = cgs.group_identity_id
                    JOIN group_settings gs ON cgs.setting_id = gs.id
                    JOIN group_content gc ON gs.content_id = gc.id
                    WHERE gi.station_id=%s AND gi.plugin_type=%s AND gi.plugin_name=%s AND gi.group_name=%s
                    LIMIT 1
                    """,
                    (self.station_id, plugin_type, plugin.name, group_name)
                )
                row_any = cur.fetchone()
            finally:
                cur.close()

            if row_any:
                row = cast(dict[str, Any], row_any)
                pdata = row.get('group_json')
                if isinstance(pdata, (bytes, bytearray)):
                    pdata = pdata.decode('utf-8')
                try:
                    mapping = json.loads(cast(str, pdata))
                except Exception:
                    logger.error("Failed to parse group JSON for %s.%s.%s", plugin_type, plugin.name, group_name)
                    mapping = {}
                # Apply values to existing BaseParameter instances if present
                for param_name, param in group.items():
                    if param_name in mapping:
                        param.value = mapping[param_name]
                continue

    def delete_plugin(self, plugin_type: str, plugin_name: str):
        cur = self.conn.cursor()
        try:
            cur.execute(
                """DELETE FROM group_identity WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s""",
                (self.station_id, plugin_type, plugin_name)
            )
            self.conn.commit()
        finally:
            cur.close()

    def delete_group(self, plugin_type: str, plugin_name: str, group_name: str):
        cur = self.conn.cursor()
        try:
            cur.execute(
                """DELETE FROM group_identity WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s AND group_name=%s""",
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            self.conn.commit()
        finally:
            cur.close()

    def wipeDB(self) -> None:
        """Very dangerous: drop Cerberus-related tables from the connected database.

        This uses DROP TABLE IF EXISTS so it is tolerant to missing tables, but
        will irreversibly remove persisted data. Callers should require explicit
        confirmation before invoking.
        """
        tables = [
            'current_group_setting',
            'group_settings',
            'group_content',
            'group_identity',
            'equipment',
            'station',
            'testplans',
            'calcables',
        ]
        cur = self.conn.cursor()
        try:
            for t in tables:
                try:
                    cur.execute(f"DROP TABLE IF EXISTS {t}")
                    logger.warning(f"Dropped table if existed: {t}")
                except Exception as ex:  # pragma: no cover - defensive
                    logger.error(f"Failed to drop table {t}: {ex}")
            self.conn.commit()
        finally:
            cur.close()

    # ------------------------------------------------------------------------------------------------------------
    def checkGroupContentIntegrity(self) -> list[tuple[int, str, str]]:
        """Verify each row in group_content matches its stored SHA256 hash.

        Returns list of (content_id, stored_hash, recomputed_hash) for mismatches.
        Empty list means all rows verified. Warns via logging on mismatch.
        """
        cur = self.conn.cursor()
        mismatches: list[tuple[int, str, str]] = []
        total = 0
        try:
            cur.execute("SELECT id, group_hash, group_json FROM group_content")
            rows = cur.fetchall()  # type: ignore[assignment]  # (id, group_hash, group_json)
            for cid_raw, stored_hash_raw, group_json in rows:
                # Assume DB returns correct types; coerce to str/int defensively
                try:
                    cid: int = int(cast(Any, cid_raw))
                except Exception:
                    continue
                stored_hash = str(stored_hash_raw)
                total += 1
                # group_json may arrive as dict (already decoded) or string
                try:
                    if isinstance(group_json, (dict, list)):
                        obj = group_json
                    elif isinstance(group_json, (bytes, bytearray, memoryview)):
                        obj = json.loads(bytes(group_json).decode('utf-8'))
                    else:
                        obj = json.loads(str(group_json))

                except Exception:
                    mismatches.append((cid, stored_hash, '<unparseable>'))
                    continue

                canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
                recomputed = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
                if recomputed != stored_hash:
                    mismatches.append((cid, stored_hash, recomputed))

        finally:
            cur.close()

        if mismatches:
            logger.warning(
                f"Group content integrity check: {len(mismatches)}/{total} mismatches detected."  # noqa: E501
            )
        else:
            logger.info(f"Group content integrity check: all {total} rows verified.")

        return mismatches

    # ------------------------------------------------------------------------------------------------------------
    def cleanup_duplicate_group_settings(self, dry_run: bool = False) -> dict[str, Any]:
        """Detect and (optionally) remove legacy duplicate rows in group_settings.

        Background: Prior to adding UNIQUE (group_identity_id, content_id) duplicates could appear
        under concurrent saves. New schema prevents future duplicates, but old ones may remain.

        Steps:
          1. Identify duplicate sets (gid, content_id) with COUNT(*) > 1.
          2. Choose the smallest id as canonical keep_id.
          3. Repoint current_group_setting rows referencing any other duplicate id to keep_id.
          4. Delete non-canonical duplicate rows (unless dry_run=True).

        Args:
            dry_run: If True, no modifications are committed; a report is returned only.

        Returns a report dict containing counts and per-duplicate details.
        """
        report: dict[str, Any] = {
            "duplicate_sets": 0,
            "rows_deleted": 0,
            "rows_kept": 0,
            "details": []
        }

        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT group_identity_id, content_id,
                       COUNT(*) AS cnt,
                       MIN(id) AS keep_id,
                       GROUP_CONCAT(id ORDER BY id) AS all_ids
                FROM group_settings
                GROUP BY group_identity_id, content_id
                HAVING cnt > 1
                """
            )
            dup_rows = cur.fetchall()
            if not dup_rows:
                return report

            report["duplicate_sets"] = len(dup_rows)

            # Use a transaction so we can rollback completely on error
            if not dry_run:
                cur.execute("START TRANSACTION")

            total_deleted = 0
            total_kept = 0
            details: list[dict[str, Any]] = []

            for group_identity_id_raw, content_id_raw, cnt_raw, keep_id_raw, all_ids_raw in dup_rows:
                try:
                    group_identity_id = int(cast(Any, group_identity_id_raw))
                    content_id = int(cast(Any, content_id_raw))
                    keep_id = int(cast(Any, keep_id_raw))
                except Exception:
                    continue
                all_ids = str(all_ids_raw)
                try:
                    id_list = [int(x) for x in all_ids.split(',') if x]
                except Exception:
                    id_list = []
                if not id_list:
                    continue
                keep_id_int = keep_id
                dup_ids = [i for i in id_list if i != keep_id]
                total_kept += 1

                # Repoint current_group_setting referencing duplicate ids
                if dup_ids and not dry_run:
                    placeholders = ','.join(['%s'] * len(dup_ids))
                    params: list[Any] = [keep_id_int, group_identity_id, *dup_ids]
                    cur.execute(
                        f"""
                        UPDATE current_group_setting
                        SET setting_id=%s
                        WHERE group_identity_id=%s AND setting_id IN ({placeholders})
                        """,
                        params
                    )

                # Delete duplicate rows
                deleted_this = 0
                if dup_ids and not dry_run:
                    cur.execute(
                        f"""
                        DELETE FROM group_settings
                        WHERE id IN ({','.join(['%s']*len(dup_ids))})
                        """,
                        tuple(dup_ids)
                    )
                    deleted_this = cur.rowcount
                    total_deleted += deleted_this

                details.append({
                    "group_identity_id": group_identity_id,
                    "content_id": content_id,
                    "keep_id": keep_id_int,
                    "duplicate_ids": dup_ids,
                    "deleted": deleted_this if not dry_run else 0
                })

            if not dry_run:
                try:
                    self.conn.commit()
                except Exception as ex:  # pragma: no cover - defensive
                    try:
                        self.conn.rollback()
                    except Exception:
                        pass
                    logger.error(f"Duplicate cleanup failed; rolled back: {ex}")
                    return report

            report.update({
                "rows_deleted": total_deleted,
                "rows_kept": total_kept,
                "details": details,
                "dry_run": dry_run,
            })

            level = logger.info if total_deleted == 0 else logger.warning
            level(
                f"Duplicate cleanup report: sets={report['duplicate_sets']} kept={total_kept} "
                f"deleted={total_deleted} dry_run={dry_run}"
            )
            return report
        finally:
            cur.close()

    # Convenience bulk helpers ------------------------------------------------------------------------------------
    def save_equipment(self, equipment_plugins: Iterable[BasePlugin]):
        self.save_many('equipment', equipment_plugins)

    def save_tests(self, test_plugins: Iterable[BasePlugin]):
        self.save_many('test', test_plugins)

    def save_products(self, product_plugins: Iterable[BasePlugin]):
        self.save_many('product', product_plugins)

    def load_equipment_into(self, plugin: BasePlugin):
        self.load_plugin_into('equipment', plugin)

    def load_test_into(self, plugin: BasePlugin):
        self.load_plugin_into('test', plugin)

    def load_product_into(self, plugin: BasePlugin):
        self.load_plugin_into('product', plugin)
