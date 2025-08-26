import logging
import zlib
from typing import Any, cast

import pyodbc

from Cerberus.common import DBInfo
from Cerberus.database.cerberusDB import CerberusDB
from Cerberus.logConfig import getLogger

logger = getLogger("MsSqlDB")
logger.setLevel(logging.INFO)


class MsSqlDB(CerberusDB):
    """Microsoft SQL Server persistence for plugin parameter settings.
    """

    def __init__(self, station_id: str, dbInfo: DBInfo):
        super().__init__(station_id)
        self.db_info = dbInfo

        try:
            self.connectToDatabase(dbInfo)
            logger.info("Database connection established successfully")

        except pyodbc.Error as err:
            error_msg = self.handleDBErrors(err)
            raise ConnectionError(error_msg) from err

        except Exception as err:
            error_msg = f"Unexpected error connecting to database: {err}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from err

        try:
            self._ensure_tables()
            logger.info("Database tables verified/created successfully")

        except pyodbc.Error as table_err:
            logger.error(f"Failed to create/verify database tables: {table_err}")
            self.conn.close()
            raise ConnectionError(f"Database table setup failed: {table_err}") from table_err

        invalidContent = self.checkGroupContentIntegrity()
        if len(invalidContent) > 0:
            logger.error("Database integrity: Broken!")
            logger.error("Group Content is invalid on these entries:")
            for id, badHash, goodHash in invalidContent:
                logger.error(f"ID:{id}: {badHash} should be: {goodHash}")
        else:
            logger.info("Database integrity: OK")

    def handleDBErrors(self, err) -> str:
        error_msg = f"Failed to connect to MSSQL database: {err}"
        logger.error(error_msg)

        # MSSQL-specific error codes
        if "Login failed" in str(err):
            logger.error("Check your username and password")
        elif "Cannot open database" in str(err):
            logger.error("Database does not exist or access denied")
        elif "server was not found" in str(err) or "network-related" in str(err):
            logger.error("Could not connect to MSSQL server - check host and port")
        elif "timeout" in str(err).lower():
            logger.error("Connection timeout - check network connectivity")

        return error_msg

    def connectToDatabase(self, dbInfo):
        logger.info(f"Connecting to MSSQL database at {dbInfo.host}:{dbInfo.port}")

        # Build connection string for MSSQL with SSL/certificate options
        connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={dbInfo.host},{dbInfo.port};"
            f"DATABASE={dbInfo.database};"
            f"UID={dbInfo.username};"
            f"PWD={dbInfo.password};"
            f"CONNECTION_TIMEOUT=10;"
            f"COMMAND_TIMEOUT=30;"
        )

        # Add SSL/encryption options
        if hasattr(dbInfo, 'encrypt') and dbInfo.encrypt:
            connection_string += "ENCRYPT=yes;"
            if hasattr(dbInfo, 'trust_server_certificate') and dbInfo.trust_server_certificate:
                connection_string += "TRUSTSERVERCERTIFICATE=yes;"
            else:
                connection_string += "TRUSTSERVERCERTIFICATE=no;"
        else:
            connection_string += "ENCRYPT=no;"

        # Add certificate path if specified
        if hasattr(dbInfo, 'certificate_path') and dbInfo.certificate_path:
            connection_string += f"SERVERCERT={dbInfo.certificate_path};"

        # Log connection string (with password masked)
        masked_connection = connection_string.replace(dbInfo.password, "***") if dbInfo.password else connection_string
        logger.info(f"Connection string: {masked_connection}")

        self.conn = pyodbc.connect(connection_string, autocommit=False)

    def _close_impl(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def _execute_catch_table_already_exists(self, cur, sql: str):
        try:
            cur.execute(sql)
        except pyodbc.Error as e:
            # MSSQL: Object already exists error
            if "already an object named" in str(e):
                pass  # Table already exists
            else:
                raise

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
            self._execute_catch_table_already_exists(cur,
                                                     """
                CREATE TABLE group_identity (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    station_id NVARCHAR(100) NOT NULL,
                    plugin_type NVARCHAR(32) NOT NULL,
                    plugin_name NVARCHAR(128) NOT NULL,
                    group_name NVARCHAR(128) NOT NULL,
                    CONSTRAINT uq_group_identity UNIQUE (station_id, plugin_type, plugin_name, group_name)
                )
                """
                                                     )

            # Global content table (one row per unique canonical JSON blob)
            self._execute_catch_table_already_exists(cur,
                                                     """
                CREATE TABLE group_content (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    group_hash CHAR(64) NOT NULL UNIQUE,
                    group_json NVARCHAR(MAX) NOT NULL,
                    created_at DATETIME2 DEFAULT GETDATE()
                )
                """
                                                     )

            # Historical immutable versions mapping identity -> content
            self._execute_catch_table_already_exists(cur,
                                                     """
                CREATE TABLE group_settings (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    group_identity_id BIGINT NOT NULL,
                    content_id BIGINT NOT NULL,
                    created_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT uq_gid_content UNIQUE (group_identity_id, content_id),
                    CONSTRAINT fk_gs_identity FOREIGN KEY (group_identity_id)
                        REFERENCES group_identity(id) ON DELETE CASCADE,
                    CONSTRAINT fk_gs_content FOREIGN KEY (content_id)
                        REFERENCES group_content(id)
                )
                """
                                                     )

            # Create indexes for group_settings if they don't exist
            try:
                cur.execute("CREATE INDEX idx_gid_created ON group_settings (group_identity_id, id)")
            except pyodbc.Error:
                pass  # Index might already exist

            try:
                cur.execute("CREATE INDEX idx_gid_content ON group_settings (group_identity_id, content_id)")
            except pyodbc.Error:
                pass  # Index might already exist

            # Pointer to current version
            self._execute_catch_table_already_exists(cur,
                                                     """
                CREATE TABLE current_group_setting (
                    group_identity_id BIGINT PRIMARY KEY,
                    setting_id BIGINT NOT NULL,
                    updated_at DATETIME2 DEFAULT GETDATE(),
                    CONSTRAINT fk_cgs_identity FOREIGN KEY (group_identity_id)
                        REFERENCES group_identity(id) ON DELETE CASCADE,
                    CONSTRAINT fk_cgs_setting FOREIGN KEY (setting_id)
                        REFERENCES group_settings(id) ON DELETE NO ACTION
                )
                """
                                                     )

            # Create index for current_group_setting if it doesn't exist
            try:
                cur.execute("CREATE INDEX idx_setting_id ON current_group_setting (setting_id)")
            except pyodbc.Error:
                pass  # Index might already exist

            # Test results table for storing test execution results
            self._execute_catch_table_already_exists(cur,
                                                     """
                CREATE TABLE test_results (
                    id BIGINT IDENTITY(1,1) PRIMARY KEY,
                    station_id NVARCHAR(100) NOT NULL,
                    test_name NVARCHAR(255) NOT NULL,
                    status NVARCHAR(50) NOT NULL,
                    timestamp DATETIME2 NOT NULL DEFAULT GETDATE(),
                    log_text NVARCHAR(MAX) NULL,
                    compressed_log VARBINARY(MAX) NULL,
                    test_result_json NVARCHAR(MAX) NOT NULL,
                    created_at DATETIME2 DEFAULT GETDATE()
                )
                """
                                                     )

            # Create indexes for test_results if they don't exist
            try:
                cur.execute("CREATE INDEX idx_test_name_timestamp ON test_results (test_name, timestamp DESC)")
            except pyodbc.Error:
                pass  # Index might already exist

            try:
                cur.execute("CREATE INDEX idx_station_test ON test_results (station_id, test_name)")
            except pyodbc.Error:
                pass  # Index might already exist

            try:
                cur.execute("CREATE INDEX idx_timestamp ON test_results (timestamp DESC)")
            except pyodbc.Error:
                pass  # Index might already exist

            self.conn.commit()
        finally:
            cur.close()

    # ------------------------------------------------------------------------------------------------------------
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
                WHERE gi.station_id=? AND gi.plugin_type=? AND gi.plugin_name=? AND gi.group_name=?
                """,
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            row = read_cur.fetchone()
            if row:
                existing_hash = str(row[0])
                if existing_hash == group_hash:
                    return  # No change needed
        finally:
            read_cur.close()

        cur = self.conn.cursor()
        try:
            # Resolve / create identity
            # MSSQL doesn't have LAST_INSERT_ID() trick, so we use MERGE or separate SELECT/INSERT
            cur.execute(
                """
                MERGE group_identity AS target
                USING (SELECT ? AS station_id, ? AS plugin_type, ? AS plugin_name, ? AS group_name) AS source
                ON target.station_id = source.station_id 
                   AND target.plugin_type = source.plugin_type 
                   AND target.plugin_name = source.plugin_name 
                   AND target.group_name = source.group_name
                WHEN NOT MATCHED THEN
                    INSERT (station_id, plugin_type, plugin_name, group_name)
                    VALUES (source.station_id, source.plugin_type, source.plugin_name, source.group_name);
                """,
                (self.station_id, plugin_type, plugin_name, group_name)
            )

            # Get the identity ID
            cur.execute(
                """
                SELECT id FROM group_identity 
                WHERE station_id=? AND plugin_type=? AND plugin_name=? AND group_name=?
                """,
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            gid = cur.fetchone()[0]

            # Locate or insert global content row
            cur.execute("SELECT id FROM group_content WHERE group_hash=?", (group_hash,))
            row = cur.fetchone()
            if row:
                content_id = int(row[0])
            else:
                try:
                    cur.execute(
                        "INSERT INTO group_content (group_hash, group_json) VALUES (?, ?)",
                        (group_hash, canonical_json)
                    )
                    # Get the inserted ID
                    cur.execute("SELECT @@IDENTITY")
                    content_id = int(cur.fetchone()[0])
                except pyodbc.Error as e:
                    if "duplicate key" in str(e).lower() or "violation of unique key" in str(e).lower():
                        # Race condition: another session inserted the same hash
                        cur.execute("SELECT id FROM group_content WHERE group_hash=?", (group_hash,))
                        content_id = int(cur.fetchone()[0])
                    else:
                        raise

            # Does this identity already have a historical setting pointing to this content?
            cur.execute(
                "SELECT id FROM group_settings WHERE group_identity_id=? AND content_id=?",
                (gid, content_id)
            )
            existing_for_identity = cur.fetchone()

            if existing_for_identity is not None:
                setting_id = int(existing_for_identity[0])
                # Only change current_group_setting if it is missing or points at a different setting.
                cur.execute(
                    """
                    UPDATE current_group_setting
                    SET setting_id=?, updated_at=GETDATE()
                    WHERE group_identity_id=? AND setting_id<>?
                    """,
                    (setting_id, gid, setting_id)
                )
                if cur.rowcount == 0:
                    # Either no row exists or it already points to the correct setting
                    cur.execute(
                        """
                        IF NOT EXISTS (SELECT 1 FROM current_group_setting WHERE group_identity_id=?)
                        INSERT INTO current_group_setting (group_identity_id, setting_id)
                        VALUES (?, ?)
                        """,
                        (gid, gid, setting_id)
                    )
            else:
                # Insert new historical version
                cur.execute(
                    "INSERT INTO group_settings (group_identity_id, content_id) VALUES (?, ?)",
                    (gid, content_id)
                )
                # Get the inserted ID
                cur.execute("SELECT @@IDENTITY")
                new_setting_id = int(cur.fetchone()[0])

                # Point current_group_setting at the new setting
                cur.execute(
                    """
                    UPDATE current_group_setting
                    SET setting_id=?, updated_at=GETDATE()
                    WHERE group_identity_id=? AND setting_id<>?
                    """,
                    (new_setting_id, gid, new_setting_id)
                )
                if cur.rowcount == 0:
                    # No existing row, insert new one
                    cur.execute(
                        "INSERT INTO current_group_setting (group_identity_id, setting_id) VALUES (?, ?)",
                        (gid, new_setting_id)
                    )

                logger.debug(
                    f"Group: '{group_name}' for plugin '{plugin_name}' changed; created new setting_id={new_setting_id} (gid={gid}) hash={group_hash}."
                )

            self.conn.commit()

        except pyodbc.Error as err:
            try:
                self.conn.rollback()
            except Exception:
                pass
            logger.error(f"Failed to save group {plugin_name}.{group_name}: {err}")
            raise

        finally:
            cur.close()

    # ------------------------------------------------------------------------------------------------------------
    def _load_group_json(self, plugin_type: str, plugin_name: str, group_name: str) -> dict:
        """Load group JSON data for a specific plugin group."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT gc.group_json FROM group_identity gi
                JOIN current_group_setting cgs ON gi.id = cgs.group_identity_id
                JOIN group_settings gs ON cgs.setting_id = gs.id
                JOIN group_content gc ON gs.content_id = gc.id
                WHERE gi.station_id=? AND gi.plugin_type=? AND gi.plugin_name=? AND gi.group_name=?
                """,
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            row = cur.fetchone()
        finally:
            cur.close()

        if row:
            pdata = row[0]
            if isinstance(pdata, (bytes, bytearray)):
                pdata = pdata.decode('utf-8')
            try:
                import json
                return json.loads(pdata)
            except Exception:
                return {}
        return {}

    def _get_cerberus_tables(self) -> list[str]:
        """Return list of Cerberus table names for MSSQL."""
        return [
            'current_group_setting',
            'group_settings',
            'group_content',
            'group_identity',
            'test_results',
            'equipment',
            'station',
            'testplans',
            'calcables',
        ]

    def _delete_plugin_impl(self, plugin_type: str, plugin_name: str):
        """MSSQL-specific implementation for deleting a plugin."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                "DELETE FROM group_identity WHERE station_id=? AND plugin_type=? AND plugin_name=?",
                (self.station_id, plugin_type, plugin_name)
            )
            self.conn.commit()
        finally:
            cur.close()

    def _delete_group_impl(self, plugin_type: str, plugin_name: str, group_name: str):
        """MSSQL-specific implementation for deleting a group."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                "DELETE FROM group_identity WHERE station_id=? AND plugin_type=? AND plugin_name=? AND group_name=?",
                (self.station_id, plugin_type, plugin_name, group_name)
            )
            self.conn.commit()
        finally:
            cur.close()

    def _drop_tables_safely(self, tables: list[str]) -> None:
        """MSSQL-specific implementation for dropping multiple tables safely."""
        cur = self.conn.cursor()
        try:
            for table_name in tables:
                cur.execute(f"IF OBJECT_ID('{table_name}', 'U') IS NOT NULL DROP TABLE {table_name}")
            self.conn.commit()
        finally:
            cur.close()

    def _get_group_content_rows(self) -> list[tuple[Any, Any, Any]]:
        """MSSQL-specific implementation to get all group_content rows."""
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT id, group_hash, group_json FROM group_content")
            return cur.fetchall()
        finally:
            cur.close()

    # ===== TEST RESULTS IMPLEMENTATION =====

    def _save_test_result_impl(self, test_name: str, status: str, timestamp,
                               log_text: str | None, compressed_log: bytes | None,
                               test_result_json: str) -> int:
        """MSSQL-specific implementation for saving test results."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO test_results (station_id, test_name, status, timestamp, log_text, compressed_log, test_result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (self.station_id, test_name, status, timestamp, log_text, compressed_log, test_result_json)
            )
            # Get the inserted ID
            cur.execute("SELECT @@IDENTITY")
            result_id = int(cur.fetchone()[0])
            self.conn.commit()
            return result_id
        except pyodbc.Error as err:
            try:
                self.conn.rollback()
            except Exception:
                pass
            logger.error(f"Failed to save test result for {test_name}: {err}")
            raise
        finally:
            cur.close()

    def _load_test_results_impl(self, test_name: str, limit: int, offset: int) -> list[dict]:
        """MSSQL-specific implementation for loading test results."""
        cur = self.conn.cursor()
        try:
            # MSSQL uses OFFSET/FETCH for pagination
            cur.execute(
                """
                SELECT id, station_id, test_name, status, timestamp, log_text, compressed_log, test_result_json, created_at
                FROM test_results
                WHERE station_id = ? AND test_name = ?
                ORDER BY timestamp DESC, id DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """,
                (self.station_id, test_name, offset, limit)
            )

            # Get column names
            columns = [column[0] for column in cur.description]
            results = []

            for row in cur.fetchall():
                result = dict(zip(columns, row))

                # Handle compressed logs
                if result.get("compressed_log") and not result.get("log_text"):
                    try:
                        result["log_text"] = self._decompress_log(result["compressed_log"])
                    except Exception as e:
                        logger.warning(f"Failed to decompress log for result {result.get('id')}: {e}")
                        result["log_text"] = "[Log decompression failed]"

                # Remove compressed_log from response to save space
                result.pop("compressed_log", None)
                results.append(result)

            return results
        finally:
            cur.close()

    def _get_test_result_by_id_impl(self, test_name: str, result_id: int) -> dict | None:
        """MSSQL-specific implementation for getting test result by ID."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT id, station_id, test_name, status, timestamp, log_text, compressed_log, test_result_json, created_at
                FROM test_results
                WHERE station_id = ? AND test_name = ? AND id = ?
                """,
                (self.station_id, test_name, result_id)
            )
            row = cur.fetchone()

            if not row:
                return None

            # Get column names and create dict
            columns = [column[0] for column in cur.description]
            result = dict(zip(columns, row))

            # Decompress log if needed
            if result.get("compressed_log") and not result.get("log_text"):
                try:
                    result["log_text"] = self._decompress_log(result["compressed_log"])
                except Exception as e:
                    logger.warning(f"Failed to decompress log for result {result_id}: {e}")
                    result["log_text"] = "[Log decompression failed]"

            # Remove compressed_log from response to save space
            result.pop("compressed_log", None)

            return result
        finally:
            cur.close()

    def _delete_test_result_impl(self, test_name: str, result_id: int) -> bool:
        """MSSQL-specific implementation for deleting a test result."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                "DELETE FROM test_results WHERE station_id = ? AND test_name = ? AND id = ?",
                (self.station_id, test_name, result_id)
            )
            deleted = cur.rowcount > 0
            self.conn.commit()
            return deleted
        except pyodbc.Error as err:
            try:
                self.conn.rollback()
            except Exception:
                pass
            logger.error(f"Failed to delete test result {result_id} for {test_name}: {err}")
            raise
        finally:
            cur.close()

    def _cleanup_old_test_results_impl(self, test_name: str, keep_count: int) -> int:
        """MSSQL-specific implementation for cleaning up old test results."""
        cur = self.conn.cursor()
        try:
            # First, get the IDs to delete using a CTE
            cur.execute(
                """
                WITH RankedResults AS (
                    SELECT id, ROW_NUMBER() OVER (ORDER BY timestamp DESC, id DESC) as rn
                    FROM test_results
                    WHERE station_id = ? AND test_name = ?
                )
                SELECT id FROM RankedResults WHERE rn > ?
                """,
                (self.station_id, test_name, keep_count)
            )

            ids_to_delete = [row[0] for row in cur.fetchall()]

            if not ids_to_delete:
                return 0

            # Delete the old results using IN clause
            placeholders = ','.join(['?' for _ in ids_to_delete])
            cur.execute(
                f"DELETE FROM test_results WHERE id IN ({placeholders})",
                ids_to_delete
            )
            deleted_count = cur.rowcount
            self.conn.commit()
            return deleted_count
        except pyodbc.Error as err:
            try:
                self.conn.rollback()
            except Exception:
                pass
            logger.error(f"Failed to cleanup old test results for {test_name}: {err}")
            raise
        finally:
            cur.close()

    # MSSQL-specific methods that contain MSSQL-specific logic ------------------------
    def checkGroupContentIntegrity(self) -> list[tuple[int, str, str]]:
        """Verify each row in group_content matches its stored SHA256 hash.

        Delegates to base class implementation.
        """
        return self.check_group_content_integrity()

    def cleanup_duplicate_group_settings(self, dry_run: bool = False) -> dict[str, Any]:
        """Detect and (optionally) remove legacy duplicate rows in group_settings.

        Delegates to base class implementation.
        """
        return super().cleanup_duplicate_group_settings(dry_run)

    def _find_duplicate_group_settings_impl(self) -> list[Any]:
        """MSSQL-specific implementation to find duplicate group settings."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT group_identity_id, content_id,
                       COUNT(*) AS cnt,
                       MIN(id) AS keep_id,
                       STRING_AGG(CAST(id AS NVARCHAR(MAX)), ',') WITHIN GROUP (ORDER BY id) AS all_ids
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
        """MSSQL-specific implementation to cleanup a single duplicate set."""
        if not dup_ids or dry_run:
            return 0

        cur = self.conn.cursor()
        try:
            # Start transaction
            cur.execute("BEGIN TRANSACTION")

            # Repoint current_group_setting referencing duplicate ids
            self._update_setting_references(group_identity_id, keep_id_int, dup_ids, cur)

            # Delete duplicate rows
            deleted_count = self._delete_rows_by_ids(dup_ids, cur)

            # Commit transaction
            self._commit_with_rollback_safety(cur)

            return deleted_count
        except Exception:
            try:
                cur.execute("ROLLBACK TRANSACTION")
            except Exception:
                pass
            raise
        finally:
            cur.close()

    def _update_setting_references(self, group_identity_id: int, new_setting_id: int,
                                   old_setting_ids: list[int], cur) -> None:
        """Update current_group_setting to point to a new setting ID."""
        placeholders = ','.join(['?' for _ in old_setting_ids])
        params = [new_setting_id, group_identity_id, *old_setting_ids]
        cur.execute(
            f"""
            UPDATE current_group_setting
            SET setting_id=?
            WHERE group_identity_id=? AND setting_id IN ({placeholders})
            """,
            params
        )

    def _delete_rows_by_ids(self, table_ids: list[int], cur) -> int:
        """Delete rows from group_settings table by IDs and return count of deleted rows."""
        placeholders = ','.join(['?' for _ in table_ids])
        cur.execute(
            f"DELETE FROM group_settings WHERE id IN ({placeholders})",
            table_ids
        )
        return cur.rowcount

    def _commit_with_rollback_safety(self, cur) -> None:
        """Commit the current transaction with automatic rollback on error."""
        try:
            cur.execute("COMMIT TRANSACTION")
        except Exception as ex:
            try:
                cur.execute("ROLLBACK TRANSACTION")
            except Exception:
                pass
            logger.error(f"Transaction failed; rolled back: {ex}")
            raise
