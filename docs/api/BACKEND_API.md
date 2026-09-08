# Revon backend API

The backend is a dependency-free REST/JSON layer over
`SQLiteRevonRepository`. It is intended for the local Revon frontend and
binds to `127.0.0.1` by default.

## Start the server

```powershell
python -m revon_api
```

Default locations:

- API: `http://127.0.0.1:8000`
- health check: `GET /api/health`
- OpenAPI index: `GET /api/openapi.json`
- repositories: `data/repositories/*.revon.db`

Select another port or repository directory when needed:

```powershell
python -m revon_api --port 8080 --repository-root data/local-repositories
```

The default CORS allowlist covers frontend development servers on ports 3000
and 5173. Repeat `--cors-origin` to supply an explicit allowlist.

## Endpoint summary

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/repositories` | List repository summaries |
| `POST` | `/api/repositories` | Create an empty repository |
| `POST` | `/api/repositories/{name}/open` | Verify and open repository metadata |
| `POST` | `/api/repositories/{name}/import` | Commit a complete JSON or CSV dataset |
| `POST` | `/api/repositories/{name}/commits` | Atomically apply puts and deletes |
| `GET` | `/api/repositories/{name}/history` | Return newest-first commit history |
| `GET` | `/api/repositories/{name}/versions/{version}` | Materialize a historical version |
| `GET` | `/api/repositories/{name}/compare` | Return structured version differences |
| `GET` | `/api/repositories/{name}/metrics` | Return storage, commit, and diff metrics |

Repository names accept only lowercase letters, digits, hyphens, and
underscores. The server derives every database path from the configured
repository root; clients cannot supply filesystem paths.

## Create and open

```bash
curl -X POST http://127.0.0.1:8000/api/repositories \
  -H "Content-Type: application/json" \
  -d '{"name":"research","branching_factor":8,"tree_depth":4,"hybrid_log_threshold":128}'

curl -X POST http://127.0.0.1:8000/api/repositories/research/open
```

Opening verifies SQLite integrity, object hashes, references, commit ancestry,
and `HEAD`. Repositories are reopened for each operation rather than retained
as mutable global objects.

## Import a dataset

Import an already-keyed JSON state:

```bash
curl -X POST http://127.0.0.1:8000/api/repositories/research/import \
  -H "Content-Type: application/json" \
  -d '{"state":{"1":{"id":"1","name":"Ada"}},"message":"Initial import"}'
```

Import JSON rows using one field as the state key:

```json
{
  "rows": [
    {"id": "1", "name": "Ada"},
    {"id": "2", "name": "Grace"}
  ],
  "primary_key": "id",
  "message": "Initial import"
}
```

Raw UTF-8 CSV is also accepted. The primary key is a required query parameter:

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/repositories/research/import?primary_key=id&message=CSV%20import" \
  -H "Content-Type: text/csv" \
  --data-binary @dataset.csv
```

Importing into an existing repository creates another complete-state version;
it does not overwrite history.

## Commit a batch

```bash
curl -X POST http://127.0.0.1:8000/api/repositories/research/commits \
  -H "Content-Type: application/json" \
  -d '{
    "base_version": 1,
    "puts": {
      "1": {"id":"1","name":"Ada Lovelace"},
      "3": {"id":"3","name":"Linus"}
    },
    "deletes": ["2"],
    "message": "Update names"
  }'
```

`base_version` is an optimistic-concurrency guard. A stale base receives HTTP
409 instead of silently writing over a newer `HEAD`. The entire batch and its
new nodes, changeset, commit, version, statistics, and `HEAD` update share one
SQLite transaction.

## History, checkout, comparison, and metrics

```bash
curl http://127.0.0.1:8000/api/repositories/research/history

curl "http://127.0.0.1:8000/api/repositories/research/versions/1?offset=0&limit=100"

curl "http://127.0.0.1:8000/api/repositories/research/compare?from=1&to=2&strategy=hybrid"

curl "http://127.0.0.1:8000/api/repositories/research/metrics?from=1&to=2&strategy=hybrid"
```

Comparison entries contain the key, change type, old value, and new value.
Diff metrics identify the selected Log or Merkle path and report its natural
work unit. The metrics response also includes actual SQLite file size and
per-version incremental construction statistics.

## Error format

Expected failures use an HTTP 4xx status and a stable JSON shape:

```json
{
  "error": {
    "code": "stale_base_version",
    "message": "base version 1 is stale; HEAD is 2"
  }
}
```

## Current security boundary

This is a local-development API. It has path containment, input limits, CORS,
structured validation, per-repository write locks, and optimistic concurrency,
but it does not yet implement authentication, TLS, rate limiting, or multi-host
locking. Keep the default loopback bind until those controls are added.
