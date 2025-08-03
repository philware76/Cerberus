import json
import logging
from dataclasses import dataclass

import mysql.connector

from Cerberus.plan import Plan


@dataclass
class dbInfo:
    host: str = "localhost"
    username: str = "root"
    password: str = ""
    database: str = "cerberus"

class Database:
    def __init__(self, stationId, dbInfo: dbInfo = dbInfo()):
        self.stationId = stationId
        self.db_info = dbInfo

        logging.debug(f"Connecting to database...")
        self.conn = mysql.connector.connect(
            host=dbInfo.host,
            user=dbInfo.username,
            password=dbInfo.password,
            database=dbInfo.database
        )

        self.ensure_station_table()
        self.ensure_testplans_table()

    def close(self):
        if self.conn:
            self.conn.close()

    def ensure_station_table(self):
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
            if cursor:
                cursor.close()

    def ensure_testplans_table(self):
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
            if cursor:
                cursor.close()

    def saveTestPlan(self, plan: Plan) -> int:
        """Save a test plan to the database and return its ID."""
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
            plan_id = -1
        
        finally:
            if cursor:
                cursor.close()

        return plan_id

    def set_TestPlanForStation(self, plan_id:int) -> bool:
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

    def set_ChamberForStation(self, chamber_type) -> bool:
        cursor = self.conn.cursor()
        query = "UPDATE station SET chamber_type = %s WHERE identity = %s"
        try:
            cursor.execute(query, (chamber_type, self.stationId))
            self.conn.commit()
            return True
        
        except mysql.connector.Error as err:
            logging.error(f"Error saving chamber for station {self.stationId}: {err}")
            return False
        
        finally:
            if cursor:
                cursor.close()

    def listTestPlans(self) -> list[Plan]:
        """List all test plans in the database."""
        plans = []
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, created_at, user FROM testplans")
            for row in cursor.fetchall():
                plan = Plan(name=row[1], date=row[2], user=row[3])
                plans.append(plan)
        
        except mysql.connector.Error as err:
            logging.error(f"Error fetching test plans: {err}")

        finally:
           if cursor:
               cursor.close()

        return plans