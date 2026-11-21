# CatScan

CatScan is organized as a monorepo so the frontend, backend, and shared examples
can be versioned together.

## Repository layout

- `frontend/` — React and TypeScript web application.
- `backend/` — Python API and document validation.
- `example/` — sample papers and documents shared by the application and tests.
- `docs/` — project documentation.

## Environment setup

Install [uv](https://docs.astral.sh/uv/) and Node.js with npm, then from the
repository root install the project's Python and JavaScript dependencies:

```sh
uv python install 3.12
cd backend && uv sync && cd ..
cd frontend && npm ci && cd ..
```

Python 3.12+ is supported by the backend configuration. Vite's development proxy
forwards `/api` requests to the backend configured in the `Procfile`.

For Indico integration routes (`/api/indico/*`), configure `CATSCAN_INTERNAL_TOKEN`
on the backend and set the same token in the Indico CatScan plugin settings
(or set `CATSCAN_REQUIRE_INDICO_AUTH=false` for local testing only).

## Run the application

From the repository root, run both development servers with Honcho:

```sh
uvx honcho start
```

Honcho reads the root `Procfile` by default. The frontend is available at
`http://127.0.0.1:3080`, and the API at `http://127.0.0.1:3060`.
