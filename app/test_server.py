import importlib.util
import json
import sqlite3
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

spec = importlib.util.spec_from_file_location("server", Path(__file__).with_name("server.py"))
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        server.DB = str(Path(self.temp.name) / "incidents.db")
        self.http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.http.server_port}"

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, payload=None, method=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(self.url + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_record_survives_new_database_connection(self):
        self.assertEqual(self.request("/incidents"), (200, []))
        status, incident = self.request("/incidents", {"title": "  Fix DNS  "})
        self.assertEqual(status, 201)
        self.assertEqual(incident["title"], "Fix DNS")
        self.assertEqual(self.request("/incidents"), (200, [incident]))

    def test_invalid_payloads_are_rejected(self):
        for payload in ({}, {"title": " "}, {"title": 42}, {"title": "x" * 201}, []):
            with self.subTest(payload=payload):
                self.assertEqual(self.request("/incidents", payload)[0], 400)

    def test_readiness_fails_but_liveness_survives_storage_failure(self):
        server.DB = str(Path(self.temp.name) / "missing" / "data.db")
        self.assertEqual(self.request("/readyz")[0], 503)
        self.assertEqual(self.request("/healthz")[0], 200)

    def test_unknown_endpoint(self):
        self.assertEqual(self.request("/missing")[0], 404)

    def test_incident_resolution_preserves_original_details(self):
        _, incident = self.request("/incidents", {"title": "API unavailable", "symptom": "No service endpoints"})
        path = f"/incidents/{incident['id']}"
        status, updated = self.request(path, {"status": "resolved", "cause": "Wrong selector",
                                              "diagnosis": "Inspected EndpointSlices", "fix": "Corrected labels",
                                              "verification": "HTTP 200"}, method="PATCH")
        self.assertEqual(status, 200)
        self.assertEqual(updated["symptom"], incident["symptom"])
        self.assertEqual(updated["created_at"], incident["created_at"])
        self.assertEqual(updated["status"], "resolved")
        self.assertEqual(self.request(path), (200, updated))

    def test_unknown_fields_and_status_are_rejected_without_changes(self):
        _, incident = self.request("/incidents", {"title": "Broken probe"})
        path = f"/incidents/{incident['id']}"
        for change in ({"status": "deleted"}, {"id": 99}, {"fix": ["invalid"]}):
            self.assertEqual(self.request(path, change, method="PATCH")[0], 400)
        self.assertEqual(self.request(path), (200, incident))
        self.assertEqual(self.request("/incidents/999", {"status": "resolved"}, method="PATCH")[0], 404)

    def test_old_database_is_migrated_without_losing_titles(self):
        with sqlite3.connect(server.DB) as db:
            db.execute("CREATE TABLE incidents (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
            db.execute("INSERT INTO incidents VALUES (1, 'Original incident')")
        status, row = self.request("/incidents/1")
        self.assertEqual(status, 200)
        self.assertEqual(row["title"], "Original incident")
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["fix"], "")


if __name__ == "__main__":
    unittest.main()
