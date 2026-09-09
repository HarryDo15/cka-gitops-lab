import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB = os.environ.get("DB_PATH", "/data/incidents.db")


def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
    return db


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            return self.reply(200, {"status": "ok"})
        if self.path == "/":
            return self.reply(200, {"app": "Incident Desk", "message": os.getenv("WELCOME_MESSAGE", "CKA practice lab"), "endpoints": ["/incidents", "/healthz", "/readyz"]})
        if self.path not in ("/incidents", "/readyz"):
            return self.reply(404, {"error": "not found"})
        try:
            with connect() as db:
                rows = db.execute("SELECT id, title FROM incidents ORDER BY id").fetchall()
            return self.reply(200, {"status": "ready"} if self.path == "/readyz" else [{"id": row[0], "title": row[1]} for row in rows])
        except sqlite3.Error:
            return self.reply(503, {"error": "database unavailable"})

    def do_POST(self):
        if self.path != "/incidents":
            return self.reply(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                raise ValueError()
            payload = json.loads(self.rfile.read(length))
            title = payload.get("title") if isinstance(payload, dict) else None
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
                raise ValueError()
        except (ValueError, TypeError):
            return self.reply(400, {"error": "provide a title of 1–200 characters"})
        try:
            with connect() as db:
                row = db.execute("INSERT INTO incidents(title) VALUES (?)", (title.strip(),))
            self.reply(201, {"id": row.lastrowid, "title": title.strip()})
        except sqlite3.Error:
            self.reply(503, {"error": "database unavailable"})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
