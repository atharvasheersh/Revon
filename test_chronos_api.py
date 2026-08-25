from __future__ import annotations

import http.client
import json
import shutil
import threading
import unittest
import uuid
from pathlib import Path
from typing import Any, Optional

from chronos_api import APIError, ChronosService
from chronos_api.server import build_server


class ChronosServiceValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tmp") / f"api-validation-{uuid.uuid4().hex}"
        self.service = ChronosService(self.root)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_repository_names_cannot_escape_server_root(self) -> None:
        for name in ("../outside", "Uppercase", "has space", "", ".hidden"):
            with self.subTest(name=name), self.assertRaises(APIError) as raised:
                self.service.create_repository({"name": name})
            self.assertEqual(raised.exception.status, 400)

    def test_stale_base_version_is_rejected(self) -> None:
        self.service.create_repository({"name": "demo"})
        self.service.import_dataset("demo", {"state": {"a": 1}})
        self.service.commit_batch("demo", {"base_version": 1, "puts": {"a": 2}})

        with self.assertRaises(APIError) as raised:
            self.service.commit_batch(
                "demo", {"base_version": 1, "puts": {"a": 3}}
            )

        self.assertEqual(raised.exception.status, 409)
        self.assertEqual(raised.exception.code, "stale_base_version")


class ChronosHTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tmp") / f"api-http-{uuid.uuid4().hex}"
        self.service = ChronosService(self.root)
        self.server = build_server(self.service, "127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        shutil.rmtree(self.root, ignore_errors=True)

    def request(
        self,
        method: str,
        path: str,
        payload: Optional[Any] = None,
        *,
        content_type: str = "application/json",
        raw_body: Optional[bytes] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> tuple[int, dict[str, Any], dict[str, str]]:
        body = raw_body
        if body is None and payload is not None:
            body = json.dumps(payload).encode("utf-8")
        request_headers = dict(headers or {})
        if body is not None:
            request_headers["Content-Type"] = content_type
        connection = http.client.HTTPConnection(self.host, self.port, timeout=10)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            data = response.read()
            decoded = json.loads(data) if data else {}
            return response.status, decoded, dict(response.getheaders())
        finally:
            connection.close()

    def test_complete_frontend_workflow(self) -> None:
        status, health, _ = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "ok")

        status, created, _ = self.request(
            "POST", "/api/repositories", {"name": "demo"}
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["head"], None)

        status, opened, _ = self.request(
            "POST", "/api/repositories/demo/open"
        )
        self.assertEqual(status, 200)
        self.assertEqual(opened["integrity"]["versions"], 0)

        initial_rows = [
            {"id": "1", "name": "Ada", "score": 10},
            {"id": "2", "name": "Linus", "score": 20},
        ]
        status, imported, _ = self.request(
            "POST",
            "/api/repositories/demo/import",
            {"rows": initial_rows, "primary_key": "id", "message": "initial"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(imported["head"], 1)
        self.assertEqual(imported["rows"], 2)

        status, committed, _ = self.request(
            "POST",
            "/api/repositories/demo/commits",
            {
                "base_version": 1,
                "puts": {
                    "1": {"id": "1", "name": "Ada", "score": 11},
                    "3": {"id": "3", "name": "Grace", "score": 30},
                },
                "deletes": ["2"],
                "message": "scores and roster",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(committed["head"], 2)
        self.assertEqual(committed["commit_metrics"]["changed_keys"], 3)

        status, history, _ = self.request(
            "GET", "/api/repositories/demo/history"
        )
        self.assertEqual(status, 200)
        self.assertEqual([item["version"] for item in history["commits"]], [2, 1])

        status, checkout, _ = self.request(
            "GET", "/api/repositories/demo/versions/1?offset=0&limit=1"
        )
        self.assertEqual(status, 200)
        self.assertEqual(checkout["returned_rows"], 1)
        self.assertTrue(checkout["truncated"])
        self.assertEqual(checkout["state"]["1"]["name"], "Ada")

        status, comparison, _ = self.request(
            "GET", "/api/repositories/demo/compare?from=1&to=2&strategy=hybrid"
        )
        self.assertEqual(status, 200)
        self.assertEqual(comparison["changed_keys"], 3)
        self.assertEqual(
            {entry["change_type"] for entry in comparison["differences"]},
            {"added", "deleted", "modified"},
        )
        self.assertEqual(comparison["diff_metrics"]["strategy_selected"], "log")

        status, metrics, _ = self.request(
            "GET", "/api/repositories/demo/metrics?from=1&to=2"
        )
        self.assertEqual(status, 200)
        self.assertGreater(metrics["storage_bytes"], 0)
        self.assertEqual(len(metrics["commit_metrics"]), 2)
        self.assertEqual(metrics["comparison"]["changed_keys"], 3)

        status, listed, _ = self.request("GET", "/api/repositories")
        self.assertEqual(status, 200)
        self.assertEqual(listed["repositories"][0]["name"], "demo")

    def test_raw_csv_import_and_cors_preflight(self) -> None:
        self.request("POST", "/api/repositories", {"name": "csv-demo"})
        status, imported, _ = self.request(
            "POST",
            "/api/repositories/csv-demo/import?primary_key=id&message=csv",
            raw_body=b"id,name\n1,Ada\n2,Grace\n",
            content_type="text/csv; charset=utf-8",
        )
        self.assertEqual(status, 201)
        self.assertEqual(imported["rows"], 2)

        status, checkout, _ = self.request(
            "GET", "/api/repositories/csv-demo/versions/1"
        )
        self.assertEqual(status, 200)
        self.assertEqual(checkout["state"]["2"]["name"], "Grace")

        status, _, headers = self.request(
            "OPTIONS",
            "/api/repositories",
            headers={"Origin": "http://localhost:5173"},
        )
        self.assertEqual(status, 204)
        self.assertEqual(
            headers["Access-Control-Allow-Origin"], "http://localhost:5173"
        )

    def test_structured_errors_and_openapi(self) -> None:
        status, duplicate, _ = self.request(
            "POST", "/api/repositories", {"name": "demo"}
        )
        self.assertEqual(status, 201)
        status, duplicate, _ = self.request(
            "POST", "/api/repositories", {"name": "demo"}
        )
        self.assertEqual(status, 409)
        self.assertEqual(duplicate["error"]["code"], "repository_exists")

        status, schema, _ = self.request("GET", "/api/openapi.json")
        self.assertEqual(status, 200)
        self.assertEqual(schema["openapi"], "3.1.0")
        self.assertIn("/api/repositories/{name}/compare", schema["paths"])


if __name__ == "__main__":
    unittest.main()
