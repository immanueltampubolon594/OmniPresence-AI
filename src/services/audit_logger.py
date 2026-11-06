import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("database/audit_logs.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

class AuditLogger:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                camera_id TEXT,
                station_id TEXT,
                event_type TEXT,
                severity TEXT,
                description TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log_event(self, camera_id: str, station_id: str, event_type: str, severity: str, description: str):
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO incidents (timestamp, camera_id, station_id, event_type, severity, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, camera_id, station_id, event_type, severity, description))
        conn.commit()
        conn.close()
        print(f"[AUDIT LOG] [{severity}] {timestamp} - {camera_id} ({station_id}): {description}")

    def get_recent_incidents(self, limit=20):
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

# Global Logger Instance
audit_logger = AuditLogger()