import json
import logging
from abc import ABC, abstractmethod
from typing import Tuple

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

        self._ensure_station_table()
        self._ensure_testplans_table()
        self._checkStationExists()

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

    def close(self):
        if self.conn:
            self.conn.close()

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
        cursor = self.conn.cursor()
        query = """
            SELECT t.plan_json, t.id
            FROM station s
            JOIN testplans t ON s.testplan_id = t.id
            WHERE s.identity = %s
        """
        cursor.execute(query, (self.stationId,))
        row = cursor.fetchone()
        plan = Plan.EmptyPlan()
        try:
            if row and row[0]:
                logging.debug(f"Laoding test plan for station {self.stationId}: #{row[1]}")
                plan = Plan.from_dict(json.loads(row[0]))
            else:
                logging.warning(f"No test plan found for station {self.stationId}. Returning empty plan.")

        except mysql.connector.Error as err:
            logging.error(f"Error fetching test plan for station {self.stationId}: {err}")

        finally:
            if cursor:
                cursor.close()

        return plan

    def get_ChamberForStation(self) -> str | None:
        cursor = self.conn.cursor()
        query = "SELECT chamber_type FROM station WHERE identity = %s"
        try:
            cursor.execute(query, (self.stationId,))
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]

        except mysql.connector.Error as err:
            logging.error(f"Error fetching chamber for station {self.stationId}: {err}")
            return None

        finally:
            cursor.close()

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
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, plan_json FROM testplans")
            for row in cursor.fetchall():
                plan_id = row[0]
                planJson = json.loads(row[1])
                plan = Plan.from_dict(planJson)
                plans.append((plan_id, plan))

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
