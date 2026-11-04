from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sqlite3
import os

# SQLite is just a file on disk — no separate database server to run.
# This creates scores.db next to server.py if it doesn't already exist,
# and creates the table if it's not there yet.
DB_FILE = "scores.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            score INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

class Handler(BaseHTTPRequestHandler):

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")  # lets game.html (different origin) talk to us
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        # Browsers send this "preflight" request automatically before a cross-origin POST.
        # It's just asking "am I allowed to POST here?" — we say yes.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/":
            with open("game.html", "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/leaderboard":
            conn = sqlite3.connect(DB_FILE)
            rows = conn.execute(
                "SELECT name, score FROM scores ORDER BY score DESC LIMIT 10"
            ).fetchall()
            conn.close()
            top = [{"name": r[0], "score": r[1]} for r in rows]
            self._send_json(200, top)
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/submit-score":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
                name = str(data["name"])
                score = int(data["score"])
            except (KeyError, ValueError, json.JSONDecodeError):
                self._send_json(400, {"error": "bad request"})
                return

            conn = sqlite3.connect(DB_FILE)
            conn.execute(
                "INSERT INTO scores (name, score) VALUES (?, ?)", (name, score)
            )
            conn.commit()
            conn.close()
            self._send_json(200, {"status": "saved"})
        else:
            self._send_json(404, {"error": "not found"})


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 8000))  # Render sets PORT; falls back to 8000 locally
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Server running on port {port}")
    server.serve_forever()