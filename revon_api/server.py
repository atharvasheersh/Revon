"""Dependency-free REST server for the Revon backend service."""

from __future__ import annotations

import argparse
import csv
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlsplit

from .service import APIError, RevonService


DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def openapi_schema() -> dict[str, Any]:
    """Return a compact OpenAPI index for frontend discovery."""

    def operation(summary: str, success: str = "200") -> dict[str, Any]:
        return {
            "summary": summary,
            "responses": {
                success: {"description": "Successful operation"},
                "400": {"description": "Invalid request"},
                "404": {"description": "Repository or version not found"},
                "409": {"description": "Repository or version conflict"},
            },
        }

    repository_parameter = {
        "name": "name",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
    }
    version_parameter = {
        "name": "version",
        "in": "path",
        "required": True,
        "schema": {"type": "integer", "minimum": 1},
    }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Revon API",
            "version": "1.0.0",
            "description": "API for content-addressed structured-data versioning.",
        },
        "paths": {
            "/api/health": {"get": operation("Health check")},
            "/api/repositories": {
                "get": operation("List repositories"),
                "post": operation("Create a repository", "201"),
            },
            "/api/repositories/{name}/open": {
                "parameters": [repository_parameter],
                "post": operation("Open and integrity-check a repository"),
            },
            "/api/repositories/{name}/import": {
                "parameters": [repository_parameter],
                "post": operation(
                    "Import a JSON state, JSON rows, or a CSV dataset", "201"
                ),
            },
            "/api/repositories/{name}/commits": {
                "parameters": [repository_parameter],
                "post": operation("Atomically commit a mutation batch", "201"),
            },
            "/api/repositories/{name}/history": {
                "parameters": [repository_parameter],
                "get": operation("List commit history"),
            },
            "/api/repositories/{name}/versions/{version}": {
                "parameters": [repository_parameter, version_parameter],
                "get": operation("Checkout a version"),
            },
            "/api/repositories/{name}/compare": {
                "parameters": [repository_parameter],
                "get": operation("Compare two versions"),
            },
            "/api/repositories/{name}/metrics": {
                "parameters": [repository_parameter],
                "get": operation("Show storage, commit, and optional diff metrics"),
            },
        },
    }


def make_handler(
    service: RevonService,
    *,
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS,
    maximum_body_bytes: int = 50 * 1024 * 1024,
) -> type[BaseHTTPRequestHandler]:
    """Bind one service instance to a request-handler class."""

    allowed_origins = frozenset(cors_origins)

    class RevonRequestHandler(BaseHTTPRequestHandler):
        server_version = "RevonAPI/1.0"

        def _cors_origin(self) -> Optional[str]:
            origin = self.headers.get("Origin")
            if "*" in allowed_origins:
                return "*"
            return origin if origin in allowed_origins else None

        def _send_json(self, status: int, payload: Any) -> None:
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            origin = self._cors_origin()
            if origin is not None:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(encoded)

        def _read_body(self) -> bytes:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise APIError(411, "content_length_required", "Content-Length is required")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise APIError(400, "invalid_content_length", "invalid Content-Length") from exc
            if length < 0 or length > maximum_body_bytes:
                raise APIError(
                    413,
                    "request_too_large",
                    f"request body exceeds {maximum_body_bytes} bytes",
                )
            return self.rfile.read(length)

        def _read_json(self) -> Any:
            raw = self._read_body()
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise APIError(400, "invalid_json", "body is not valid UTF-8 JSON") from exc

        @staticmethod
        def _single(query: dict[str, list[str]], name: str) -> Optional[str]:
            values = query.get(name)
            if not values:
                return None
            if len(values) != 1:
                raise APIError(400, "invalid_parameter", f"'{name}' must occur once")
            return values[0]

        @classmethod
        def _query_integer(
            cls,
            query: dict[str, list[str]],
            name: str,
            *,
            required: bool = False,
        ) -> Optional[int]:
            value = cls._single(query, name)
            if value is None:
                if required:
                    raise APIError(
                        400,
                        "missing_parameter",
                        f"query parameter '{name}' is required",
                    )
                return None
            try:
                return int(value)
            except ValueError as exc:
                raise APIError(400, "invalid_parameter", f"'{name}' must be an integer") from exc

        def _csv_payload(self, query: dict[str, list[str]]) -> dict[str, Any]:
            primary_key = self._single(query, "primary_key")
            if not primary_key:
                raise APIError(
                    400,
                    "missing_parameter",
                    "CSV imports require the 'primary_key' query parameter",
                )
            raw = self._read_body()
            try:
                text = raw.decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(text))
                if not reader.fieldnames:
                    raise APIError(400, "invalid_csv", "CSV header is missing")
                rows = list(reader)
            except UnicodeDecodeError as exc:
                raise APIError(400, "invalid_csv", "CSV must be UTF-8 encoded") from exc
            message = self._single(query, "message")
            return {"rows": rows, "primary_key": primary_key, "message": message}

        @staticmethod
        def _segments(path: str) -> list[str]:
            return [unquote(segment) for segment in path.strip("/").split("/") if segment]

        def _dispatch_get(self) -> tuple[int, Any]:
            parsed = urlsplit(self.path)
            segments = self._segments(parsed.path)
            query = parse_qs(parsed.query, keep_blank_values=True)
            if segments == ["api", "health"]:
                return 200, {"status": "ok", "service": "revon"}
            if segments == ["api", "openapi.json"]:
                return 200, openapi_schema()
            if segments == ["api", "repositories"]:
                return 200, service.list_repositories()
            if len(segments) >= 4 and segments[:2] == ["api", "repositories"]:
                name = segments[2]
                if segments[3:] == ["history"]:
                    return 200, service.history(name)
                if len(segments) == 5 and segments[3] == "versions":
                    try:
                        version = int(segments[4])
                    except ValueError as exc:
                        raise APIError(
                            400,
                            "invalid_parameter",
                            "version must be an integer",
                        ) from exc
                    offset = self._query_integer(query, "offset") or 0
                    limit = self._query_integer(query, "limit")
                    return 200, service.checkout(name, version, offset=offset, limit=limit)
                if segments[3:] == ["compare"]:
                    left = self._query_integer(query, "from", required=True)
                    right = self._query_integer(query, "to", required=True)
                    strategy = self._single(query, "strategy") or "hybrid"
                    assert left is not None and right is not None
                    return 200, service.compare(name, left, right, strategy)
                if segments[3:] == ["metrics"]:
                    left = self._query_integer(query, "from")
                    right = self._query_integer(query, "to")
                    strategy = self._single(query, "strategy") or "hybrid"
                    return 200, service.metrics(
                        name, left=left, right=right, strategy=strategy
                    )
            raise APIError(404, "route_not_found", "route does not exist")

        def _dispatch_post(self) -> tuple[int, Any]:
            parsed = urlsplit(self.path)
            segments = self._segments(parsed.path)
            query = parse_qs(parsed.query, keep_blank_values=True)
            if segments == ["api", "repositories"]:
                return service.create_repository(self._read_json())
            if len(segments) == 4 and segments[:2] == ["api", "repositories"]:
                name, action = segments[2], segments[3]
                if action == "open":
                    # Consume an optional empty JSON object if supplied by a client.
                    if self.headers.get("Content-Length") not in {None, "0"}:
                        self._read_json()
                    return 200, service.open_repository(name)
                if action == "import":
                    content_type = self.headers.get("Content-Type", "").lower()
                    payload = (
                        self._csv_payload(query)
                        if content_type.startswith("text/csv")
                        else self._read_json()
                    )
                    return service.import_dataset(name, payload)
                if action == "commits":
                    return service.commit_batch(name, self._read_json())
            raise APIError(404, "route_not_found", "route does not exist")

        def _handle(self, method: str) -> None:
            try:
                status, payload = (
                    self._dispatch_get() if method == "GET" else self._dispatch_post()
                )
            except APIError as exc:
                self._send_json(exc.status, exc.as_dict())
            except Exception:
                self.log_error("unhandled server exception")
                self._send_json(
                    500,
                    {
                        "error": {
                            "code": "internal_server_error",
                            "message": "an unexpected server error occurred",
                        }
                    },
                )
            else:
                self._send_json(status, payload)

        def do_GET(self) -> None:
            self._handle("GET")

        def do_POST(self) -> None:
            self._handle("POST")

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            origin = self._cors_origin()
            if origin is not None:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Content-Length", "0")
            self.end_headers()

    return RevonRequestHandler


def build_server(
    service: RevonService,
    host: str,
    port: int,
    *,
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        (host, port), make_handler(service, cors_origins=cors_origins)
    )
    server.daemon_threads = True
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path("data") / "repositories",
    )
    parser.add_argument(
        "--cors-origin",
        action="append",
        dest="cors_origins",
        help="allowed browser origin; repeat for multiple origins",
    )
    args = parser.parse_args()
    origins = tuple(args.cors_origins) if args.cors_origins else DEFAULT_CORS_ORIGINS
    service = RevonService(args.repository_root)
    server = build_server(service, args.host, args.port, cors_origins=origins)
    print(f"Revon API listening on http://{args.host}:{args.port}")
    print(f"Repository root: {service.repositories.root}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Revon API")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
