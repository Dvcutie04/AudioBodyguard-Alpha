import sqlite3, time

class TelemetryLogger:
    def __init__(self, db_path="telemetry.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp_ns INTEGER, confidence REAL, pulse_count INTEGER, pattern TEXT, command TEXT, device TEXT)")

    def log_event(self, confidence, pulse_count, pattern, command, device="SmartCast"):
        with self.conn:
            self.conn.execute("INSERT INTO events (timestamp_ns, confidence, pulse_count, pattern, command, device) VALUES (?, ?, ?, ?, ?, ?)", (time.monotonic_ns(), confidence, pulse_count, pattern, command, device))
