from __future__ import annotations

import json
import logging
from typing import Any, Optional, cast

import mysql.connector

from Cerberus.common import DBInfo
from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.plan import Plan


class Database(StorageInterface):
    def __init__(self, stationId: str, dbInfo: DBInfo = DBInfo()):
        self.stationId = stationId
        self.db_info = dbInfo

        logging.debug(f"Connecting to database...")
        self.conn = mysql.connector.connect(
            host=dbInfo.host,
            port=dbInfo.port,
            user=dbInfo.username,
            password=dbInfo.password,
            database=dbInfo.database
        )

        # Ensure tables exist (order so FKs have targets)
        self._ensure_station_table()
        self._ensure_testplans_table()
        self._ensure_equipment_table()
        self._ensure_calcables_table()
        self._checkStationExists()

    def close(self):
        """Close the database connection"""
        if self.conn is not None:
            self.conn.close()
            logging.debug("Closed the MySQL database connection")

    def wipeDB(self) -> bool:
        cursor = None
        try:
            cursor = self.conn.cursor()
            # Drop station first (depends on equipment/testplans via FK to equipment only)
            cursor.execute("DROP TABLE IF EXISTS station")
            cursor.execute("DROP TABLE IF EXISTS testplans")
            cursor.execute("DROP TABLE IF EXISTS equipment")
            self.conn.commit()

            logging.warning("Database tables dropped by user command.")
            return True

        except Exception as e:
            logging.error(f"Error wiping database: {e}")
            return False

        finally:
            if cursor is not None:
                cursor.close()

    def _checkStationExists(self):
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT identity FROM station WHERE identity = %s", (self.stationId,))
            row = cursor.fetchone()
            if not row:
                # Insert new station entry if missing
                cursor.execute(
                    "INSERT INTO station (identity) VALUES (%s)",
                    (self.stationId,)
                )
                self.conn.commit()
                logging.info(f"Created new station entry for identity: {self.stationId}")
            else:
                logging.info("Station entry in Database is found")

        except mysql.connector.Error as err:
            logging.error(f"Error checking/creating station entry for {self.stationId}: {err}")

        finally:
            if cursor is not None:
                cursor.close()

    def _ensure_station_table(self):
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS station (
                identity VARCHAR(100) PRIMARY KEY,
                chamber_type VARCHAR(100),
                testplan_id INT
            )
            """)
            self.conn.commit()
        except mysql.connector.Error as err:
            logging.error(f"Error creating station table: {err}")
        finally:
            if cursor is not None:
                cursor.close()

    def _ensure_testplans_table(self):
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS testplans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user VARCHAR(100),
                plan_json TEXT NOT NULL
            )
            """)
            self.conn.commit()
        except mysql.connector.Error as err:
            logging.error(f"Error creating testplans table: {err}")
        finally:
            if cursor is not None:
                cursor.close()

    def _ensure_equipment_table(self):
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                id INT AUTO_INCREMENT PRIMARY KEY,
                station_identity VARCHAR(100) NULL,
                manufacturer VARCHAR(100) NOT NULL,
                model VARCHAR(100) NOT NULL,
                serial VARCHAR(100) NOT NULL,
                version VARCHAR(100),
                ip_address VARCHAR(64) NOT NULL,
                port INT NOT NULL,
                timeout_ms INT NOT NULL DEFAULT 1000,
                calibration_date DATE NULL,
                calibration_due DATE NULL,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_equipment_serial (serial),
                INDEX ix_equipment_station (station_identity),
                CONSTRAINT fk_equipment_station FOREIGN KEY (station_identity) REFERENCES station(identity)
            )
            """)
            self.conn.commit()
        except mysql.connector.Error as err:
            logging.error(f"Error creating equipment table: {err}")
        finally:
            if cursor is not None:
                cursor.close()

    def _ensure_calcables_table(self):
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS calcables (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    station_identity VARCHAR(100) NOT NULL,
                    role ENUM('TX','RX') NOT NULL,
                    serial VARCHAR(100) NOT NULL,
                    calibration_method VARCHAR(32) NOT NULL,
                    degree INT NOT NULL,
                    domain_min DOUBLE NOT NULL,
                    domain_max DOUBLE NOT NULL,
                    coeffs_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_calcable_station_role (station_identity, role),
                    INDEX ix_calcable_station (station_identity),
                    CONSTRAINT fk_calcables_station FOREIGN KEY (station_identity) REFERENCES station(identity)
                )
                """
            )
            self.conn.commit()
        except mysql.connector.Error as err:
            logging.error(f"Error creating calcables table: {err}")
        finally:
            if cursor is not None:
                cursor.close()

    def saveTestPlan(self, plan: Plan) -> int | None:
        """Save a test plan to the database and return its ID."""
        cursor = None
        plan_id = -1
        try:
            cursor = self.conn.cursor()
            plan_json = json.dumps(plan.to_dict())
            cursor.execute("""
                INSERT INTO testplans (name, user, plan_json)
                VALUES (%s, %s, %s)
            """, (plan.name, plan.user, plan_json))
            self.conn.commit()
            plan_id = cursor.lastrowid

        except mysql.connector.Error as err:
            logging.error(f"Error saving test plan: {err}")

        finally:
            if cursor is not None:
                cursor.close()

        return plan_id

    def set_TestPlanForStation(self, plan_id: int) -> bool:
        """Set the test plan for this station in the database, only if plan_id exists."""
        cursor = self.conn.cursor()
        try:
            # Check if plan_id exists
            cursor.execute("SELECT id FROM testplans WHERE id = %s", (plan_id,))
            exists = cursor.fetchone()
            if not exists:
                logging.error(f"Test plan ID {plan_id} does not exist in testplans table.")
                return False
            cursor.execute("""
                UPDATE station SET testplan_id = %s WHERE identity = %s
            """, (plan_id, self.stationId))
            self.conn.commit()
            return True

        except mysql.connector.Error as err:
            logging.error(f"Error setting test plan for station {self.stationId}: {err}")
            return False

        finally:
            if cursor:
                cursor.close()

    def get_TestPlanForStation(self) -> Plan:
        """Get the test plan for this station from the database using a JOIN."""
        cursor = self.conn.cursor(dictionary=True)
        query = """
            SELECT t.plan_json AS plan_json, t.id AS id
            FROM station s
            JOIN testplans t ON s.testplan_id = t.id
            WHERE s.identity = %s
        """
        cursor.execute(query, (self.stationId,))
        row = cast(Optional[dict[str, Any]], cursor.fetchone())
        plan = Plan.EmptyPlan()
        try:
            if row and row.get('plan_json'):
                logging.debug(f"Loading test plan for station {self.stationId}: #{row.get('id')}")
                plan_json_obj = row.get('plan_json')
                if isinstance(plan_json_obj, (bytes, bytearray)):
                    plan_json = plan_json_obj.decode('utf-8')
                else:
                    plan_json = cast(str, plan_json_obj)
                plan = Plan.from_dict(json.loads(plan_json))
            else:
                logging.warning(f"No test plan found for station {self.stationId}. Returning empty plan.")
        except (mysql.connector.Error, json.JSONDecodeError, ValueError, TypeError) as err:
            logging.error(f"Error fetching test plan for station {self.stationId}: {err}")
        finally:
            cursor.close()
        return plan

    def get_ChamberForStation(self) -> str | None:
        cursor = self.conn.cursor(dictionary=True)
        query = "SELECT chamber_type FROM station WHERE identity = %s"
        try:
            cursor.execute(query, (self.stationId,))
            row = cast(Optional[dict[str, Any]], cursor.fetchone())
            if row and row.get('chamber_type') is not None:
                val = row.get('chamber_type')
                if isinstance(val, (bytes, bytearray)):
                    return val.decode('utf-8')
                if isinstance(val, str):
                    return val
                return str(val)
        except mysql.connector.Error as err:
            logging.error(f"Error fetching chamber for station {self.stationId}: {err}")
            return None
        finally:
            cursor.close()
        return None

    def set_ChamberForStation(self, chamberType) -> bool:
        cursor = self.conn.cursor()
        query = "UPDATE station SET chamber_type = %s WHERE identity = %s"
        try:
            cursor.execute(query, (chamberType, self.stationId))
            self.conn.commit()
            return True

        except mysql.connector.Error as err:
            logging.error(f"Error saving chamber for station {self.stationId}: {err}")
            return False

        finally:
            if cursor:
                cursor.close()

    def listTestPlans(self) -> list[tuple[int, Plan]]:
        """List all test plans in the database."""
        plans: list[tuple[int, Plan]] = []
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT id, plan_json FROM testplans")
            for _row in cursor.fetchall():
                row = cast(dict[str, Any], _row)
                raw_json_obj = row.get('plan_json')
                if isinstance(raw_json_obj, (bytes, bytearray)):
                    raw_json = raw_json_obj.decode('utf-8')
                else:
                    raw_json = cast(str, raw_json_obj) if raw_json_obj is not None else ''
                try:
                    plan_dict = json.loads(raw_json) if raw_json else {}
                    plan = Plan.from_dict(plan_dict)
                    rid_obj = row.get('id')
                    if isinstance(rid_obj, (bytes, bytearray)):
                        rid_str = rid_obj.decode('utf-8')
                        rid = int(rid_str)
                    else:
                        rid = int(rid_obj)  # type: ignore[arg-type]
                    plans.append((rid, plan))
                except (ValueError, TypeError) as e:
                    logging.error(f"Skipping malformed plan id {row.get('id')}: {e}")
        except mysql.connector.Error as err:
            logging.error(f"Error fetching test plans: {err}")
        finally:
            if cursor:
                cursor.close()
        return plans

    def deleteTestPlan(self, plan_id: int) -> bool:
        """Delete a test plan by ID."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM testplans WHERE id = %s", (plan_id,))
            self.conn.commit()
            if cursor.rowcount > 0:
                logging.info(f"Test plan {plan_id} deleted successfully.")
                return True
            else:
                logging.warning(f"Test plan {plan_id} not found.")
                return False

        except mysql.connector.Error as err:
            logging.error(f"Error deleting test plan {plan_id}: {err}")
            return False

        finally:
            if cursor is not None:
                cursor.close()

    # Equipment management -----------------------------------------------------------------------------------------
    def upsertEquipment(self, manufacturer: str, model: str, serial: str, version: str,
                        ip: str, port: int, timeout: int, calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM equipment WHERE serial = %s", (serial,))
            row = cast(Optional[dict[str, Any]], cursor.fetchone())
            if row:
                equip_id = int(row['id'])
                cursor.execute("""
                    UPDATE equipment
                    SET manufacturer=%s, model=%s, version=%s, ip_address=%s, port=%s, timeout_ms=%s, calibration_date=%s, calibration_due=%s
                    WHERE id=%s
                """, (manufacturer, model, version, ip, port, timeout, calibration_date, calibration_due, equip_id))
                self.conn.commit()
                return equip_id
            else:
                cursor.execute("""
                    INSERT INTO equipment (manufacturer, model, serial, version, ip_address, port, timeout_ms, calibration_date, calibration_due)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (manufacturer, model, serial, version, ip, port, timeout, calibration_date, calibration_due))
                self.conn.commit()
                new_id = cursor.lastrowid  # type: ignore[assignment]
                return int(new_id) if new_id is not None else None
        except mysql.connector.Error as err:
            logging.error(f"Error upserting equipment {serial}: {err}")
            return None
        finally:
            if cursor is not None:
                cursor.close()

    def attachEquipmentToStation(self, equipmentId: int) -> bool:
        cursor = None
        try:
            cursor = self.conn.cursor()
            # Idempotent check
            cursor.execute("SELECT station_identity FROM equipment WHERE id=%s", (equipmentId,))
            raw = cursor.fetchone()
            if not raw:
                logging.error(f"Equipment id {equipmentId} not found for attachment")
                return False

            row_t = cast(tuple, raw)
            current_station = row_t[0]
            if current_station == self.stationId:
                return True

            cursor.execute("UPDATE equipment SET station_identity=%s WHERE id=%s", (self.stationId, equipmentId))
            self.conn.commit()
            return cursor.rowcount >= 0

        except mysql.connector.Error as err:
            logging.error(f"Error attaching equipment {equipmentId} to station {self.stationId}: {err}")
            return False

        finally:
            if cursor is not None:
                cursor.close()

    def listStationEquipment(self) -> list[dict[str, Any]]:
        cursor = None
        results: list[dict[str, Any]] = []
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM equipment WHERE station_identity=%s ORDER BY id", (self.stationId,))
            rows = cursor.fetchall()
            if rows:
                for r in rows:
                    results.append(cast(dict[str, Any], r))
            return results

        except mysql.connector.Error as err:
            logging.error(f"Error listing equipment for station {self.stationId}: {err}")
            return results

        finally:
            if cursor is not None:
                cursor.close()

    def fetchStationEquipmentByModel(self, model: str) -> dict[str, Any] | None:
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM equipment WHERE station_identity=%s AND model=%s LIMIT 1", (self.stationId, model))
            row = cursor.fetchone()
            if row:
                return cast(dict[str, Any], row)

            return None

        except mysql.connector.Error as err:
            logging.error(f"Error fetching equipment model '{model}' for station {self.stationId}: {err}")
            return None

        finally:
            if cursor is not None:
                cursor.close()

    # Calibration Cable management ----------------------------------------------------
    def upsertCalCable(self, role: str, serial: str, *, method: str, degree: int,
                       domain: tuple[float, float], coeffs: list[float]) -> int | None:
        role_u = role.upper()
        if role_u not in ("TX", "RX"):
            raise ValueError("role must be 'TX' or 'RX'")

        payload = {
            "method": method,
            "degree": degree,
            "domain": list(domain),
            "coeffs": coeffs
        }
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM calcables WHERE station_identity=%s AND role=%s", (self.stationId, role_u))
            row = cursor.fetchone()
            if row:
                row_d = cast(dict[str, Any], row)
                cid = int(row_d['id'])
                cursor.execute(
                    """UPDATE calcables SET serial=%s, calibration_method=%s, degree=%s, domain_min=%s, domain_max=%s, coeffs_json=%s WHERE id=%s""",
                    (serial, method, degree, domain[0], domain[1], json.dumps(payload), cid)
                )
                self.conn.commit()
                return cid
            else:
                cursor.execute(
                    """INSERT INTO calcables (station_identity, role, serial, calibration_method, degree, domain_min, domain_max, coeffs_json)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (self.stationId, role_u, serial, method, degree, domain[0], domain[1], json.dumps(payload))
                )
                self.conn.commit()
                new_id = cursor.lastrowid
                return int(new_id) if new_id is not None else None
        except mysql.connector.Error as err:
            logging.error(f"Error upserting cal cable {role_u}: {err}")
            return None
        finally:
            if cursor is not None:
                cursor.close()

    def fetchCalCable(self, role: str) -> dict[str, Any] | None:
        role_u = role.upper()
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM calcables WHERE station_identity=%s AND role=%s", (self.stationId, role_u))
            row = cursor.fetchone()
            if row:
                return cast(dict[str, Any], row)
            return None
        except mysql.connector.Error as err:
            logging.error(f"Error fetching cal cable {role_u}: {err}")
            return None
        finally:
            cursor.close()

    def listCalCables(self) -> list[dict[str, Any]]:
        cursor = self.conn.cursor(dictionary=True)
        rows: list[dict[str, Any]] = []
        try:
            cursor.execute("SELECT * FROM calcables WHERE station_identity=%s ORDER BY role", (self.stationId,))
            for r in cursor.fetchall():
                rows.append(cast(dict[str, Any], r))
            return rows
        except mysql.connector.Error as err:
            logging.error(f"Error listing cal cables: {err}")
            return rows
        finally:
            cursor.close()

    def deleteCalCable(self, role: str) -> bool:
        role_u = role.upper()
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM calcables WHERE station_identity=%s AND role=%s", (self.stationId, role_u))
            self.conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            logging.error(f"Error deleting cal cable {role_u}: {err}")
            return False
        finally:
            cursor.close()

    def buildCalCableChebyshev(self, role: str):
        row = self.fetchCalCable(role)
        if not row:
            return None, None

        coeffs_json = row.get("coeffs_json")
        if not coeffs_json:
            return None, None

        try:
            payload = json.loads(coeffs_json)
            if payload.get("method") != "chebyshev":
                logging.error("Unsupported calibration method %r", payload.get("method"))
                return None, payload
            from numpy.polynomial import Chebyshev
            coeffs = payload["coeffs"]
            domain = tuple(payload["domain"])
            ch = Chebyshev(coeffs, domain=domain)
            return ch, payload

        except Exception as e:
            logging.exception("Failed to rebuild Chebyshev for cal cable %s: %s", role, e)
            return None, None

    def buildCalCableLossFn(self, role: str):
        ch, meta = self.buildCalCableChebyshev(role)
        if ch is None:
            return lambda _f: None, meta

        return lambda f_mhz: float(ch(f_mhz)), meta

    def fetchCable(self, role: str) -> dict[str, Any] | None:
        """
        role: 'TX' or 'RX' stored in model or a dedicated field.
        Example: model='TX_CABLE' or 'RX_CABLE'.
        """
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM equipment WHERE station_identity=%s AND equipment_type='CABLE' AND model=%s LIMIT 1",
                (self.stationId, f"{role.upper()}_CABLE")
            )
            row = cursor.fetchone()
            if row:
                return cast(dict[str, Any], row)

        finally:
            cursor.close()
