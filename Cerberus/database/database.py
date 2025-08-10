import json
import logging
from typing import Any, Dict, Optional, Tuple, cast

import mysql.connector

from Cerberus.common import DBInfo
from Cerberus.database.storeageInterface import StorageInterface
from Cerberus.plan import Plan


class Database(StorageInterface):
    def __init__(self, stationId, dbInfo: DBInfo = DBInfo()):
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

        # Ensure equipment table exists before station (FK dependency)
        self._ensure_equipment_table()
        self._ensure_testplans_table()
        self._ensure_station_table()
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
                testplan_id INT,
                siggen_id INT NULL,
                specan_id INT NULL,
                CONSTRAINT fk_station_siggen FOREIGN KEY (siggen_id) REFERENCES equipment(id),
                CONSTRAINT fk_station_specan FOREIGN KEY (specan_id) REFERENCES equipment(id)
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
                role ENUM('SIGGEN','SPECAN') NOT NULL,
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
                UNIQUE KEY uq_equipment_serial (serial)
            )
            """)
            self.conn.commit()
        except mysql.connector.Error as err:
            logging.error(f"Error creating equipment table: {err}")
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
        row = cast(Optional[Dict[str, Any]], cursor.fetchone())
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
            row = cast(Optional[Dict[str, Any]], cursor.fetchone())
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

    def listTestPlans(self) -> list[Tuple[int, Plan]]:
        """List all test plans in the database."""
        plans: list[Tuple[int, Plan]] = []
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT id, plan_json FROM testplans")
            for _row in cursor.fetchall():
                row = cast(Dict[str, Any], _row)
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
    def upsertEquipment(self, equipRole: str, manufacturer: str, model: str, serial: str, version: str,
                        ip: str, port: int, timeout: int, calibration_date: str | None = None, calibration_due: str | None = None) -> int | None:
        equipRole = equipRole.upper()
        if equipRole not in ("SIGGEN", "SPECAN"):
            logging.error(f"Invalid equipment role '{equipRole}' (expected SIGGEN|SPECAN)")
            return None
        cursor = None
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM equipment WHERE serial = %s", (serial,))
            row = cast(Optional[Dict[str, Any]], cursor.fetchone())
            if row:
                equip_id = int(row['id'])
                cursor.execute("""
                    UPDATE equipment
                    SET role=%s, manufacturer=%s, model=%s, version=%s, ip_address=%s, port=%s, timeout_ms=%s, calibration_date=%s, calibration_due=%s
                    WHERE id=%s
                """, (equipRole, manufacturer, model, version, ip, port, timeout, calibration_date, calibration_due, equip_id))
                self.conn.commit()
                return equip_id
            else:
                cursor.execute("""
                    INSERT INTO equipment (role, manufacturer, model, serial, version, ip_address, port, timeout_ms, calibration_date, calibration_due)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (equipRole, manufacturer, model, serial, version, ip, port, timeout, calibration_date, calibration_due))
                self.conn.commit()
                new_id = cursor.lastrowid  # type: ignore[assignment]
                if new_id is None:
                    return None
                return int(new_id)
        except mysql.connector.Error as err:
            logging.error(f"Error upserting equipment {serial}: {err}")
            return None
        finally:
            if cursor is not None:
                cursor.close()

    def assignEquipmentToStation(self, equipRole: str, equipmentId: int) -> bool:
        role = equipRole.upper()
        if role == 'SIGGEN':
            field = 'siggen_id'
        elif role == 'SPECAN':
            field = 'specan_id'
        else:
            logging.error(f"Unknown equipment role {equipRole} for assignment")
            return False
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"UPDATE station SET {field}=%s WHERE identity=%s", (equipmentId, self.stationId))
            self.conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            logging.error(f"Error assigning equipment {equipmentId} to station {self.stationId}: {err}")
            return False
        finally:
            if cursor is not None:
                cursor.close()

    def getStationEquipment(self) -> Dict[str, Dict[str, Any]]:
        cursor = None
        result: Dict[str, Dict[str, Any]] = {}
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT s.siggen_id, s.specan_id,
                       sg.role as sg_role, sg.manufacturer as sg_manufacturer, sg.model as sg_model, sg.serial as sg_serial, sg.version as sg_version, sg.ip_address as sg_ip, sg.port as sg_port, sg.timeout_ms as sg_timeout, sg.calibration_date as sg_cal_date, sg.calibration_due as sg_cal_due,
                       sa.role as sa_role, sa.manufacturer as sa_manufacturer, sa.model as sa_model, sa.serial as sa_serial, sa.version as sa_version, sa.ip_address as sa_ip, sa.port as sa_port, sa.timeout_ms as sa_timeout, sa.calibration_date as sa_cal_date, sa.calibration_due as sa_cal_due
                FROM station s
                LEFT JOIN equipment sg ON s.siggen_id = sg.id
                LEFT JOIN equipment sa ON s.specan_id = sa.id
                WHERE s.identity = %s
            """, (self.stationId,))
            row = cast(Optional[Dict[str, Any]], cursor.fetchone())
            if not row:
                return result
            if row.get('siggen_id'):
                result['SIGGEN'] = {
                    'id': row.get('siggen_id'), 'role': row.get('sg_role'), 'manufacturer': row.get('sg_manufacturer'), 'model': row.get('sg_model'),
                    'serial': row.get('sg_serial'), 'version': row.get('sg_version'), 'ip': row.get('sg_ip'), 'port': row.get('sg_port'), 'timeout': row.get('sg_timeout'),
                    'calibration_date': row.get('sg_cal_date'), 'calibration_due': row.get('sg_cal_due')
                }
            if row.get('specan_id'):
                result['SPECAN'] = {
                    'id': row.get('specan_id'), 'role': row.get('sa_role'), 'manufacturer': row.get('sa_manufacturer'), 'model': row.get('sa_model'),
                    'serial': row.get('sa_serial'), 'version': row.get('sa_version'), 'ip': row.get('sa_ip'), 'port': row.get('sa_port'), 'timeout': row.get('sa_timeout'),
                    'calibration_date': row.get('sa_cal_date'), 'calibration_due': row.get('sa_cal_due')
                }
            return result
        except mysql.connector.Error as err:
            logging.error(f"Error retrieving station equipment for {self.stationId}: {err}")
            return result
        finally:
            if cursor is not None:
                cursor.close()
