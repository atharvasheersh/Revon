# Commit note: frontend-ready backend API

- Date: 2026-08-23
- Commit: `d3c9593`
- Author: atharvasheersh
- Scope: api

## Objective

Expose the durable Revon workflows required by the final frontend without
changing the fixed-depth Merkle trie or SQLite persistence model.

## Changes

- Added server-controlled repository creation, listing, opening, and integrity
  verification.
- Added keyed JSON state, JSON row, and raw UTF-8 CSV imports.
- Added atomic puts/deletes with optimistic `base_version` conflict detection.
- Added history, paginated checkout, structured comparison, construction
  metrics, storage size, and Log/Merkle diff metrics.
- Added a threaded dependency-free HTTP server, browser CORS allowlist,
  structured errors, request-size limits, and an OpenAPI endpoint.
- Added service and real HTTP integration tests for the complete frontend flow.

## Verification

```text
python -m unittest -v
Ran 40 tests in 8.016s; OK
```

## Design decisions

Repository names, not client paths, select files beneath one server-owned
root. Repositories reopen per operation so SQLite remains the durable source of
truth. Writes are protected by both an in-process repository lock and a stale
base-version check.

## Known limitations

- Authentication, TLS, rate limiting, and multi-host locking are not included;
  the server therefore binds to loopback by default.
- Checkout and comparison can return large responses when pagination is not
  requested or when versions contain many differences.

## Next action

Connect the frontend repository, import, history, checkout, comparison, and
metrics screens to these stable routes.
