import importlib.util
import json
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

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = Request(self.url + path, data=data, headers={"Content-Type": "application/json"})
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


if __name__ == "__main__":
    unittest.main()
