import json
import mysql.connector

from plugins.baseParameters import BaseParameter, BaseParameters
from plugins.tests.TxLevelTest.TxLevelTest import TxLevelTestParameters

class ParameterDB:
    def __init__(self, host="localhost", user="root", password="5m1thMy3r5", database="cerberus"):
        self.conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        self.ensure_table()

    def ensure_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_parameters (
            id INT AUTO_INCREMENT PRIMARY KEY,
            test_name VARCHAR(100) NOT NULL,
            group_name VARCHAR(100) NOT NULL,
            parameters_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.conn.commit()

    def save_parameters(self, test_name: str, group_name: str, base_params: BaseParameters):
        json_str = json.dumps(base_params.to_dict())
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO test_parameters (test_name, group_name, parameters_json)
            VALUES (%s, %s, %s)
        """, (test_name, group_name, json_str))
        self.conn.commit()

    def load_latest_parameters(self, test_name: str, group_name: str) -> BaseParameters:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT parameters_json FROM test_parameters
            WHERE test_name = %s AND group_name = %s
            ORDER BY created_at DESC LIMIT 1
        """, (test_name, group_name))
        row = cursor.fetchone()
        if row:
            return BaseParameters.from_dict(json.loads(row[0]))
        else:
            raise ValueError("No parameters found for that test/group.")

def main():
    db = ParameterDB()

    # Example BaseParameters
    params = TxLevelTestParameters()

    # Save to DB
    db.save_parameters("TxLevelTest", "RF Sweep", params)

    # Load back
    loaded = db.load_latest_parameters("TxLevelTest", "RF Sweep")
    for name, param in loaded.parameters.items():
        print(f"{name}: {param.value} {param.unit or ''}")

if __name__ == "__main__":
    main()