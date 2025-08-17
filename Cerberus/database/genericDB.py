import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional, cast

import mysql.connector

from Cerberus.common import DBInfo
from Cerberus.database.baseDB import BaseDB
from Cerberus.plugins.baseParameters import BaseParameter
from Cerberus.plugins.basePlugin import BasePlugin


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
        self._ensure_table()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    # ------------------------------------------------------------------------------------------------------------
    def _ensure_table(self):
        """Ensure new refactored tables exist.

        Refactor: original single `settings` table has been split into:
          - group_settings: immutable history of versions (one row per distinct content change)
          - station_settings: pointer to current version (one row per station/plugin/group)
        """
        cur = self.conn.cursor()
        try:
            # Historical versions table (content-address-like via hash duplication avoidance handled in code)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_settings (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    station_id VARCHAR(100) NOT NULL,
                    plugin_type VARCHAR(32) NOT NULL,
                    plugin_name VARCHAR(128) NOT NULL,
                    group_name VARCHAR(128) NOT NULL,
                    group_json JSON NOT NULL,
                    group_hash CHAR(64) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    KEY idx_group_identity (station_id, plugin_type, plugin_name, group_name),
                    KEY idx_group_hash (group_hash)
                )
                """
            )

            # Current version pointer table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS station_settings (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    station_id VARCHAR(100) NOT NULL,
                    plugin_type VARCHAR(32) NOT NULL,
                    plugin_name VARCHAR(128) NOT NULL,
                    group_name VARCHAR(128) NOT NULL,
                    settingID BIGINT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_station_group (station_id, plugin_type, plugin_name, group_name),
                    KEY idx_settingID (settingID),
                    CONSTRAINT fk_station_settings_settingID FOREIGN KEY (settingID) REFERENCES group_settings(id)
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
        Save an entire parameter group as one row containing JSON mapping parameter_name->value.
        If the content hash matches the latest stored version we skip inserting a new row.
        """
        group_hash, canonical_json = self.compute_group_hash(values_map)
        cur = self.conn.cursor()
        try:
            # Fetch latest stored hash for this group (if any)
            cur.execute(
                """
                SELECT group_hash FROM group_settings
                WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s AND group_name=%s
                ORDER BY id DESC LIMIT 1
                """,
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            row = cur.fetchone()
            if row and row[0] == group_hash:  # type: ignore[index]
                return  # No change in content -> don't insert new version

            # Insert new immutable version row
            cur.execute(
                """
                INSERT INTO group_settings (station_id, plugin_type, plugin_name, group_name, group_json, group_hash)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (self.station_id, plugin_type, plugin_name, group_name, canonical_json, group_hash)
            )
            new_id = cur.lastrowid

            # Upsert pointer row for current version
            cur.execute(
                """
                INSERT INTO station_settings (station_id, plugin_type, plugin_name, group_name, settingID)
                VALUES (%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE settingID=VALUES(settingID)
                """,
                (self.station_id, plugin_type, plugin_name, group_name, new_id)
            )

            logging.debug(f"Group: {group_name} for plugin {plugin_name} changed, new settingID={new_id}.")
            self.conn.commit()
        except mysql.connector.Error as err:  # pragma: no cover - operational
            logging.error(f"Failed to save group {plugin_name}.{group_name}: {err}")
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
                    SELECT gs.group_json FROM station_settings ss
                    INNER JOIN group_settings gs ON ss.settingID = gs.id
                    WHERE ss.station_id=%s AND ss.plugin_type=%s AND ss.plugin_name=%s AND ss.group_name=%s
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
                    logging.error("Failed to parse group JSON for %s.%s.%s", plugin_type, plugin.name, group_name)
                    mapping = {}
                # Apply values to existing BaseParameter instances if present
                for param_name, param in group.items():
                    if param_name in mapping:
                        param.value = mapping[param_name]
                continue

    def delete_plugin(self, plugin_type: str, plugin_name: str):
        cur = self.conn.cursor()
        try:
            # Remove pointer row(s) then historical rows
            cur.execute(
                """DELETE FROM station_settings WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s""",
                (self.station_id, plugin_type, plugin_name)
            )
            cur.execute(
                """DELETE FROM group_settings WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s""",
                (self.station_id, plugin_type, plugin_name)
            )
            self.conn.commit()
        finally:
            cur.close()

    def delete_group(self, plugin_type: str, plugin_name: str, group_name: str):
        cur = self.conn.cursor()
        try:
            cur.execute(
                """DELETE FROM station_settings WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s AND group_name=%s""",
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            cur.execute(
                """DELETE FROM group_settings WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s AND group_name=%s""",
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
            'station_settings',
            'group_settings',
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
                    logging.warning(f"Dropped table if existed: {t}")
                except Exception as ex:  # pragma: no cover - defensive
                    logging.error(f"Failed to drop table {t}: {ex}")
            self.conn.commit()
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
