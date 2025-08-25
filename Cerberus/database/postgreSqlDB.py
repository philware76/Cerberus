import json
import logging
from typing import Any, cast

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from Cerberus.common import DBInfo
from Cerberus.database.cerberusDB import CerberusDB
from Cerberus.logConfig import getLogger

logger = getLogger("Database")
logger.setLevel(logging.INFO)


class PostgreSqlDB(CerberusDB):
    """PostgreSQL persistence for plugin parameter settings.
    """

    def __init__(self, station_id: str, dbInfo: DBInfo):
        super().__init__(station_id)
        self.db_info = dbInfo

        try:
            self.connectToDatabase(dbInfo)
            logger.info("Database connection established successfully")

        except psycopg.Error as err:
            error_msg = self.handleDBErrors(err)
            raise ConnectionError(error_msg) from err

        except Exception as err:
            error_msg = f"Unexpected error connecting to database: {err}"
            logger.error(error_msg)

            raise ConnectionError(error_msg) from err

        try:
            self._ensure_tables()
            logger.info("Database tables verified/created successfully")

        except psycopg.Error as table_err:
            logger.error(f"Failed to create/verify database tables: {table_err}")
            self.conn.close()

            raise ConnectionError(f"Database table setup failed: {table_err}") from table_err

        invalidContent = self.check_group_content_integrity()
        if len(invalidContent) > 0:
            logger.error("Database integrity: Broken!")
            logger.error("Group Content is invalid on these entries:")
            for id, badHash, goodHash in invalidContent:
                logger.error(f"ID:{id}: {badHash} should be: {goodHash}")

        else:
            logger.info("Database integrity: OK")

    def handleDBErrors(self, err) -> str:
        error_msg = f"Failed to connect to PostgreSQL database: {err}"
        logger.error(error_msg)

        # PostgreSQL error handling
        if hasattr(err, 'sqlstate'):
            if err.sqlstate == '28000':  # Invalid authorization specification
                logger.error("Check your username and password")
            elif err.sqlstate == '3D000':  # Invalid catalog name
                logger.error("Database does not exist")
            elif err.sqlstate == '08006':  # Connection failure
                logger.error("Could not connect to PostgreSQL server - check host and port")
            elif err.sqlstate in ('08000', '08003', '08S01'):  # Connection exceptions
                logger.error("Connection error - check network connectivity")

        return error_msg

    def connectToDatabase(self, dbInfo):
        logger.info(f"Connecting to PostgreSQL database at {dbInfo.host}:{dbInfo.port}...")
        connection_string = f"host={dbInfo.host} port={dbInfo.port} dbname={dbInfo.database} user={dbInfo.username} password={dbInfo.password}"
        self.conn = psycopg.connect(
            connection_string,
            autocommit=False,
            connect_timeout=10,
            options="-c client_encoding=UTF8"
        )

    def _close_impl(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def _execute_catch_table_already_exists(self, cur, sql_query: str):
        try:
            cur.execute(sql_query)
        except psycopg.errors.DuplicateTable:
            pass  # Table already exists
        except psycopg.Error as e:
            # Check if it's a "relation already exists" error
            if "already exists" in str(e):
                pass
            else:
                raise

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
            self._execute_catch_table_already_exists(cur,
                                                     """
                CREATE TABLE IF NOT EXISTS group_identity (
                    id BIGSERIAL PRIMARY KEY,
                    station_id VARCHAR(100) NOT NULL,
                    plugin_type VARCHAR(32) NOT NULL,
                    plugin_name VARCHAR(128) NOT NULL,
                    group_name VARCHAR(128) NOT NULL,
                    UNIQUE (station_id, plugin_type, plugin_name, group_name)
                )
                """
                                                     )

            # Global content table (one row per unique canonical JSON blob)
            self._execute_catch_table_already_exists(cur,
                                                     """
                CREATE TABLE IF NOT EXISTS group_content (
                    id BIGSERIAL PRIMARY KEY,
                    group_hash CHAR(64) NOT NULL UNIQUE,
                    group_json JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                                                     )

            # Historical immutable versions mapping identity -> content
            self._execute_catch_table_already_exists(cur,
                                                     """
                CREATE TABLE IF NOT EXISTS group_settings (
                    id BIGSERIAL PRIMARY KEY,
                    group_identity_id BIGINT NOT NULL,
                    content_id BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (group_identity_id, content_id),
                    CONSTRAINT fk_gs_identity FOREIGN KEY (group_identity_id)
                        REFERENCES group_identity(id) ON DELETE CASCADE,
                    CONSTRAINT fk_gs_content FOREIGN KEY (content_id)
                        REFERENCES group_content(id) ON DELETE RESTRICT
                )
                """
                                                     )

            # Create indexes
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS idx_gid_created ON group_settings(group_identity_id, id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_gid_content ON group_settings(group_identity_id, content_id)")
            except psycopg.Error:
                pass  # Index might already exist

            # Pointer to current version
            self._execute_catch_table_already_exists(cur,
                                                     """
                CREATE TABLE IF NOT EXISTS current_group_setting (
                    group_identity_id BIGINT PRIMARY KEY,
                    setting_id BIGINT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_cgs_identity FOREIGN KEY (group_identity_id)
                        REFERENCES group_identity(id) ON DELETE CASCADE,
                    CONSTRAINT fk_cgs_setting FOREIGN KEY (setting_id)
                        REFERENCES group_settings(id) ON DELETE CASCADE
                )
                """
                                                     )

            # Create index for setting_id
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS idx_setting_id ON current_group_setting(setting_id)")
            except psycopg.Error:
                pass  # Index might already exist

            self.conn.commit()
        finally:
            cur.close()

    def _save_group_imp(self, plugin_type: str, plugin_name: str, group_name: str, values_map: dict) -> None:
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
            # Resolve / create identity (PostgreSQL equivalent of MySQL's ON DUPLICATE KEY UPDATE)
            cur.execute(
                """
                INSERT INTO group_identity (station_id, plugin_type, plugin_name, group_name)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (station_id, plugin_type, plugin_name, group_name) 
                DO UPDATE SET id = group_identity.id
                RETURNING id
                """,
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            result = cur.fetchone()
            gid = result[0] if result else None

            # Locate or insert global content row WITHOUT burning an AUTO_INCREMENT value when
            # the hash already exists. This SELECT -> INSERT approach reduces (but
            # cannot eliminate) gaps. A race where another session inserts the same hash between
            # our SELECT and INSERT is handled by catching unique constraint violation and re-selecting.
            cur.execute("SELECT id FROM group_content WHERE group_hash=%s", (group_hash,))
            row = cur.fetchone()
            if row:
                content_id = int(row[0])  # type: ignore[index]
            else:
                try:
                    cur.execute(
                        "INSERT INTO group_content (group_hash, group_json) VALUES (%s,%s) RETURNING id",
                        (group_hash, canonical_json)
                    )
                    result = cur.fetchone()
                    content_id = result[0] if result else None
                except psycopg.errors.UniqueViolation:  # pragma: no cover - race condition path
                    # Another connection inserted concurrently; fetch the id now present.
                    cur.execute("SELECT id FROM group_content WHERE group_hash=%s", (group_hash,))
                    content_id = int(cur.fetchone()[0])  # type: ignore[index]

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
                    SET setting_id=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE group_identity_id=%s AND setting_id<>%s
                    """,
                    (setting_id, gid, setting_id)
                )
                if cur.rowcount == 0:
                    # Either the pointer already matches (no action needed) OR the row is absent.
                    # 2. Insert it if absent (ON CONFLICT DO NOTHING avoids error if it actually existed and matched).
                    cur.execute(
                        """
                        INSERT INTO current_group_setting (group_identity_id, setting_id)
                        VALUES (%s,%s)
                        ON CONFLICT (group_identity_id) DO NOTHING
                        """,
                        (gid, setting_id)
                    )
                self.conn.commit()
                logger.debug(
                    f"Group: '{group_name}' for plugin '{plugin_name}' unchanged; reused existing setting_id={setting_id} (gid={gid}) hash={group_hash}."
                )
                return

            # Insert (or reuse existing) historical version referencing shared content.
            # PostgreSQL equivalent with ON CONFLICT
            cur.execute(
                """
                INSERT INTO group_settings (group_identity_id, content_id) VALUES (%s,%s)
                ON CONFLICT (group_identity_id, content_id) DO UPDATE SET id = group_settings.id
                RETURNING id
                """,
                (gid, content_id)
            )
            result = cur.fetchone()
            new_setting_id = result[0] if result else None

            # Point current_group_setting at the new/reused setting only if different or missing.
            cur.execute(
                """
                UPDATE current_group_setting
                SET setting_id=%s, updated_at=CURRENT_TIMESTAMP
                WHERE group_identity_id=%s AND setting_id<>%s
                """,
                (new_setting_id, gid, new_setting_id)
            )
            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO current_group_setting (group_identity_id, setting_id)
                    VALUES (%s,%s)
                    ON CONFLICT (group_identity_id) DO NOTHING
                    """,
                    (gid, new_setting_id)
                )

            self.conn.commit()
            logger.debug(
                f"Group: '{group_name}' for plugin '{plugin_name}' changed; created new setting_id={new_setting_id} (gid={gid}) hash={group_hash}."
            )

        except psycopg.Error as err:  # pragma: no cover - operational
            try:
                self.conn.rollback()
            except Exception:
                pass
            logger.error(f"Failed to save group {plugin_name}.{group_name}: {err}")

        finally:
            cur.close()

    def _load_group_json(self, plugin_type: str, plugin_name: str, group_name: str) -> dict:
        """Load group JSON data for a specific plugin group."""
        cur = self.conn.cursor(row_factory=dict_row)
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
                (self.station_id, plugin_type, plugin_name, group_name)
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
                if isinstance(pdata, dict):
                    return pdata  # PostgreSQL JSONB returns dict directly
                return json.loads(cast(str, pdata))
            except Exception:
                logger.error("Failed to parse group JSON for %s.%s.%s", plugin_type, plugin_name, group_name)
        return {}

    def _get_cerberus_tables(self) -> list[str]:
        """Return list of Cerberus table names for PostgreSQL."""
        return [
            'current_group_setting',
            'group_settings',
            'group_content',
            'group_identity',
            'equipment',
            'station',
            'testplans',
            'calcables',
        ]

    def _delete_plugin_impl(self, plugin_type: str, plugin_name: str):
        """PostgreSQL-specific implementation for deleting a plugin."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """DELETE FROM group_identity WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s""",
                (self.station_id, plugin_type, plugin_name)
            )
            self.conn.commit()
        finally:
            cur.close()

    def _delete_group_impl(self, plugin_type: str, plugin_name: str, group_name: str):
        """PostgreSQL-specific implementation for deleting a group."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """DELETE FROM group_identity WHERE station_id=%s AND plugin_type=%s AND plugin_name=%s AND group_name=%s""",
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            self.conn.commit()
        finally:
            cur.close()

    def _drop_tables_safely(self, tables: list[str]) -> None:
        """PostgreSQL-specific implementation for dropping multiple tables safely."""
        cur = self.conn.cursor()
        try:
            for table_name in tables:
                try:
                    # Use sql.SQL for safe table name construction
                    query = sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(table_name))
                    cur.execute(query)
                    logger.warning(f"Dropped table if existed: {table_name}")
                except Exception as ex:  # pragma: no cover - defensive
                    logger.error(f"Failed to drop table {table_name}: {ex}")
            self.conn.commit()
        finally:
            cur.close()

    def _get_group_content_rows(self) -> list[tuple[Any, Any, Any]]:
        """PostgreSQL-specific implementation to get all group_content rows."""
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT id, group_hash, group_json FROM group_content")
            return cur.fetchall()  # type: ignore[return-value]
        finally:
            cur.close()

    # PostgreSQL-specific database implementation methods ------------------------
    def _find_duplicate_group_settings_impl(self) -> list[Any]:
        """PostgreSQL-specific implementation to find duplicate group settings."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT group_identity_id, content_id,
                       COUNT(*) AS cnt,
                       MIN(id) AS keep_id,
                       STRING_AGG(id::text, ',' ORDER BY id) AS all_ids
                FROM group_settings
                GROUP BY group_identity_id, content_id
                HAVING COUNT(*) > 1
                """
            )
            return cur.fetchall()
        finally:
            cur.close()

    def _cleanup_single_duplicate_set_impl(self, group_identity_id: int, keep_id_int: int,
                                           dup_ids: list[int], dry_run: bool) -> int:
        """PostgreSQL-specific implementation to cleanup a single duplicate set."""
        if not dup_ids or dry_run:
            return 0

        cur = self.conn.cursor()
        try:
            # Start transaction
            cur.execute("BEGIN")

            # Repoint current_group_setting referencing duplicate ids
            self._update_setting_references(group_identity_id, keep_id_int, dup_ids, cur)

            # Delete duplicate rows
            deleted_count = self._delete_rows_by_ids(dup_ids, cur)

            # Commit transaction
            self._commit_with_rollback_safety(cur)

            return deleted_count
        except Exception:
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise
        finally:
            cur.close()

    def _update_setting_references(self, group_identity_id: int, new_setting_id: int,
                                   old_setting_ids: list[int], cur) -> None:
        """Update current_group_setting to point to a new setting ID."""
        placeholders = ','.join(['%s'] * len(old_setting_ids))
        params: list[Any] = [new_setting_id, group_identity_id, *old_setting_ids]
        cur.execute(
            f"""
            UPDATE current_group_setting
            SET setting_id=%s, updated_at=CURRENT_TIMESTAMP
            WHERE group_identity_id=%s AND setting_id IN ({placeholders})
            """,
            params
        )

    def _delete_rows_by_ids(self, table_ids: list[int], cur) -> int:
        """Delete rows from group_settings table by IDs and return count of deleted rows."""
        cur.execute(
            f"""
            DELETE FROM group_settings
            WHERE id IN ({','.join(['%s']*len(table_ids))})
            """,
            tuple(table_ids)
        )
        return cur.rowcount

    def _commit_with_rollback_safety(self, cur) -> None:
        """Commit the current transaction with automatic rollback on error."""
        try:
            self.conn.commit()
        except Exception as ex:  # pragma: no cover - defensive
            try:
                self.conn.rollback()
            except Exception:
                pass
            logger.error(f"Transaction failed; rolled back: {ex}")
            raise
