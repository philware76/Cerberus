import configparser

import mysql.connector


class Database:
    def __init__(self, ini_path="cerberus.ini"):
        config = configparser.ConfigParser()
        config.read(ini_path)
        db_cfg = config["database"]
        self.station_identity = config["cerberus"]["identity"]
        self.conn = mysql.connector.connect(
            host=db_cfg.get("host", "localhost"),
            user=db_cfg.get("username", "root"),
            password=db_cfg.get("password", ""),
            database=db_cfg.get("database", "cerberus")
        )
        self.ensure_station_table()

    def close(self):
        if self.conn:
            self.conn.close()

    def ensure_station_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS station (
            identity VARCHAR(100) PRIMARY KEY,
            chamber_type VARCHAR(100)
        )
        """)
        self.conn.commit()
        cursor.close()

    def get_station_chamber_type(self):
        cursor = self.conn.cursor()
        query = "SELECT chamber_type FROM station WHERE identity = %s"
        cursor.execute(query, (self.station_identity,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result[0]
        return None

    def set_station_chamber_type(self, chamber_type):
        cursor = self.conn.cursor()
        query = """
        INSERT INTO station (identity, chamber_type)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE chamber_type = VALUES(chamber_type)
        """
        cursor.execute(query, (self.station_identity, chamber_type))
        self.conn.commit()
        cursor.close()
