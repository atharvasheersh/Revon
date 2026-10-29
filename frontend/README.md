# Revon frontend

The final Revon workspace is a responsive React/Vinext interface for the
local Python backend. It supports the complete demonstration path:

- create, list, and open repositories;
- import UTF-8 CSV or JSON datasets;
- commit atomic put/delete batches with optimistic concurrency;
- inspect commit history and materialize an earlier version;
- compare any two versions through Revon-H, forced Merkle, or forced Log;
- view storage, structural-sharing, diff-work, and integrity metrics.

## Run locally

Start the backend from the repository root:

```powershell
python -m revon_api
```

Then start the frontend in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend expects the API at
`http://127.0.0.1:8000/api`; use the connection control in the lower-left
corner to change it.

## Verify

```powershell
npm run lint
npm test
npm audit
```

`npm test` performs a production build and checks the server-rendered product
surface. Backend HTTP behavior is covered by
`python -m unittest discover -s tests -v`
from the repository root.

The image-generation dependencies are pinned to patched `@vercel/og` and
`fflate` releases. The install script embeds HarfBuzz's installed WASM binary
into the OG library's Node and worker bundles, which otherwise omit that asset.
It checks the library version and loader layout before modifying either bundle.
Run installation with scripts enabled; `npm test` verifies PNG generation through
the framework's `ImageResponse`, as well as the existing workspace checks.

## Deployment boundary

The current backend deliberately binds to loopback and has no authentication,
TLS, or rate limiting. The hosted frontend is therefore a private product
preview; use the local two-process setup for the complete interactive demo.
