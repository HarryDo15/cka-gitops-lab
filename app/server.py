import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB = os.environ.get("DB_PATH", "/data/incidents.db")
FIELDS = {"title": 200, "symptom": 4000, "cause": 4000, "diagnosis": 4000,
          "fix": 4000, "verification": 4000, "status": 20}
SCHEMA_LOCK = threading.Lock()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        # Additive migration preserves records from the initial title-only app.
        with SCHEMA_LOCK, db:
            db.execute("CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
            columns = {row[1] for row in db.execute("PRAGMA table_info(incidents)")}
            for field in ("symptom", "cause", "diagnosis", "fix", "verification", "status", "created_at", "updated_at"):
                if field not in columns:
                    default = "open" if field == "status" else ""
                    db.execute(f"ALTER TABLE incidents ADD COLUMN {field} TEXT NOT NULL DEFAULT '{default}'")
        with db:
            yield db
    finally:
        db.close()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def incident_id(self):
        match = re.fullmatch(r"/incidents/([1-9][0-9]{0,17})", self.path)
        return int(match[1]) if match else None

    def do_GET(self):
        if self.path == "/healthz":
            return self.reply(200, {"status": "ok"})
        if self.path == "/":
            return self.reply(200, {"app": "Incident Desk", "message": os.getenv("WELCOME_MESSAGE", "CKA practice lab"),
                                    "endpoints": ["/incidents", "/incidents/{id}", "/healthz", "/readyz"]})
        incident_id = self.incident_id()
        if self.path not in ("/incidents", "/readyz") and incident_id is None:
            return self.reply(404, {"error": "not found"})
        try:
            with connect() as db:
                if self.path == "/readyz":
                    db.execute("SELECT 1 FROM incidents LIMIT 1")
                    result = {"status": "ready"}
                elif incident_id:
                    row = db.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
                    if row is None:
                        return self.reply(404, {"error": "incident not found"})
                    result = dict(row)
                else:
                    result = [dict(row) for row in db.execute("SELECT * FROM incidents ORDER BY id")]
            self.reply(200, result)
        except sqlite3.Error:
            self.reply(503, {"error": "database unavailable"})

    def payload(self, creating):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32768:
                raise ValueError("provide a JSON body of at most 32768 bytes")
            data = json.loads(self.rfile.read(length))
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("invalid JSON body")
        if not isinstance(data, dict) or not data or set(data) - FIELDS.keys():
            raise ValueError("provide only supported incident fields")
        if creating and "title" not in data:
            raise ValueError("title is required")
        for field, value in data.items():
            if not isinstance(value, str) or len(value.strip()) > FIELDS[field]:
                raise ValueError(f"{field} must be text of at most {FIELDS[field]} characters")
            data[field] = value.strip()
        if "title" in data and not data["title"]:
            raise ValueError("title must not be empty")
        if "status" in data and data["status"] not in ("open", "investigating", "resolved"):
            raise ValueError("status must be open, investigating, or resolved")
        return data

    def write_incident(self, creating):
        incident_id = self.incident_id()
        if (creating and self.path != "/incidents") or (not creating and incident_id is None):
            return self.reply(404, {"error": "not found"})
        try:
            data = self.payload(creating)
        except ValueError as error:
            return self.reply(400, {"error": str(error)})
        try:
            with connect() as db:
                data["updated_at"] = timestamp()
                if creating:
                    data["created_at"] = data["updated_at"]
                    keys = ",".join(data)
                    placeholders = ",".join("?" for _ in data)
                    cursor = db.execute(f"INSERT INTO incidents ({keys}) VALUES ({placeholders})", tuple(data.values()))
                    incident_id = cursor.lastrowid
                else:
                    assignments = ",".join(f"{key}=?" for key in data)
                    cursor = db.execute(f"UPDATE incidents SET {assignments} WHERE id=?", (*data.values(), incident_id))
                    if cursor.rowcount == 0:
                        return self.reply(404, {"error": "incident not found"})
                result = dict(db.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone())
            self.reply(201 if creating else 200, result)
        except sqlite3.Error:
            self.reply(503, {"error": "database unavailable"})

    def do_POST(self):
        self.write_incident(creating=True)

    def do_PATCH(self):
        self.write_incident(creating=False)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
