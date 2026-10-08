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
uv python install 3.14
cd backend && uv sync --locked && cd ..
cd frontend && npm ci && cd ..
```

Python 3.14 is required by the backend configuration. The frontend uses Vite's
development proxy to send `/api` requests to `http://localhost:8000`, so no
environment file is needed for local development.

## Run the application

From the repository root, run both development servers with Honcho:

```sh
uvx honcho start
```

Honcho reads the root `Procfile` by default. The frontend is available at
`http://localhost:3000`, and the API at `http://localhost:8000`.
