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
    station_id: str
    plugin_type: str  # 'equipment' | 'product' | 'test'
    plugin_name: str
    group_name: str
    parameter_name: str
    parameter_json: str

    def key(self) -> tuple[str, str, str, str, str]:
        return (self.station_id, self.plugin_type, self.plugin_name, self.group_name, self.parameter_name)


class GenericDB(BaseDB):
    """Generic persistence for plugin parameter settings.

    Schema design:
      settings (
          station_id VARCHAR(100),
          plugin_type VARCHAR(32),    -- logical categorisation
          plugin_name VARCHAR(128),   -- BasePlugin.name
          group_name VARCHAR(128),    -- BaseParameters.groupName
          parameter_name VARCHAR(128),
          parameter_json JSON NOT NULL,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (station_id, plugin_type, plugin_name, group_name, parameter_name)
      )
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
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    station_id VARCHAR(100) NOT NULL,
                    plugin_type VARCHAR(32) NOT NULL,
                    plugin_name VARCHAR(128) NOT NULL,
                    group_name VARCHAR(128) NOT NULL,
                    parameter_name VARCHAR(128) NOT NULL,
                    parameter_json JSON NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (station_id, plugin_type, plugin_name, group_name, parameter_name)
                )
                """
            )
            self.conn.commit()
        finally:
            cur.close()

    # ------------------------------------------------------------------------------------------------------------
    def save_parameter(self, plugin_type: str, plugin_name: str, group_name: str, param: BaseParameter) -> None:
        rec_json = json.dumps(param.to_dict())
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO settings (station_id, plugin_type, plugin_name, group_name, parameter_name, parameter_json)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE parameter_json=VALUES(parameter_json)
                """,
                (self.station_id, plugin_type, plugin_name, group_name, param.name, rec_json)
            )
            self.conn.commit()
        except mysql.connector.Error as err:
            logging.error(f"Failed to save parameter {plugin_name}.{group_name}.{param.name}: {err}")
        finally:
            cur.close()

    def save_plugin(self, plugin_type: str, plugin: BasePlugin):
        for group_name, group in plugin._groupParams.items():  # noqa: SLF001 (internal access intentional)
            for param in group.values():
                self.save_parameter(plugin_type, plugin.name, group_name, param)

    def save_many(self, plugin_type: str, plugins: Iterable[BasePlugin]):
        for p in plugins:
            self.save_plugin(plugin_type, p)

    # ------------------------------------------------------------------------------------------------------------
    def load_parameter(self, plugin_type: str, plugin_name: str, group_name: str, parameter_name: str) -> Optional[BaseParameter]:
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute(
                """
                SELECT parameter_json FROM settings
                WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s AND group_name=%s AND parameter_name=%s
                """,
                (self.station_id, plugin_type, plugin_name, group_name, parameter_name)
            )
            row_any = cur.fetchone()
            if not row_any:
                return None

            row = cast(dict[str, Any], row_any)
            pdata = row.get('parameter_json')
            if isinstance(pdata, (bytes, bytearray)):
                pdata = pdata.decode('utf-8')

            d = json.loads(cast(str, pdata))
            p_type = d.get('type')
            from Cerberus.plugins.baseParameters import PARAMETER_TYPE_MAP
            cls = PARAMETER_TYPE_MAP.get(p_type)
            if not cls:
                logging.error(
                    "Unknown parameter type %r while loading %s.%s.%s", p_type, plugin_name, group_name, parameter_name
                )
                return None

            return cls.from_dict(d)

        finally:
            cur.close()

    def load_plugin_into(self, plugin_type: str, plugin: BasePlugin):
        for group_name, group in plugin._groupParams.items():  # noqa: SLF001
            for param_name, param in group.items():
                restored = self.load_parameter(plugin_type, plugin.name, group_name, param_name)
                if restored:
                    # Replace value only; keep original instance object for references
                    param.value = restored.value

    def load_all_for_type(self, plugin_type: str) -> list[SettingRecord]:
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute(
                """
                SELECT station_id, plugin_type, plugin_name, group_name, parameter_name, parameter_json
                FROM settings
                WHERE station_id=%s AND plugin_type=%s
                """,
                (self.station_id, plugin_type)
            )
            rows_any = cur.fetchall() or []
            result: list[SettingRecord] = []
            for r_any in rows_any:
                r = cast(dict[str, Any], r_any)
                pj = r.get('parameter_json')
                if isinstance(pj, (bytes, bytearray)):
                    pj = pj.decode('utf-8')
                result.append(
                    SettingRecord(
                        station_id=cast(str, r.get('station_id')),
                        plugin_type=cast(str, r.get('plugin_type')),
                        plugin_name=cast(str, r.get('plugin_name')),
                        group_name=cast(str, r.get('group_name')),
                        parameter_name=cast(str, r.get('parameter_name')),
                        parameter_json=cast(str, pj),
                    )
                )
            return result
        finally:
            cur.close()

    def delete_plugin(self, plugin_type: str, plugin_name: str):
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                DELETE FROM settings WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s
                """,
                (self.station_id, plugin_type, plugin_name)
            )
            self.conn.commit()
        finally:
            cur.close()

    def delete_group(self, plugin_type: str, plugin_name: str, group_name: str):
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                DELETE FROM settings WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s AND group_name=%s
                """,
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            self.conn.commit()
        finally:
            cur.close()

    def delete_parameter(self, plugin_type: str, plugin_name: str, group_name: str, parameter_name: str):
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                DELETE FROM settings WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s AND group_name=%s AND parameter_name=%s
                """,
                (self.station_id, plugin_type, plugin_name, group_name, parameter_name)
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
            'settings',
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
