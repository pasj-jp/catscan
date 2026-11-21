# CatScan frontend

React/Vite frontend for checking PASJ and JACoW manuscripts. The upload form sends Word files, LaTeX files, and source archives to `POST /api/scan/file`.

## Local development

Run `npm ci` and `npm run start`. With Vite started directly, `/api` is proxied to `http://127.0.0.1:8000`. Set `CATSCAN_API_PROXY_TARGET` when running the backend on a different port. The root `Procfile` sets this value for Honcho.

## Production API URL

The frontend uses same-origin `/api` requests by default. When the frontend and API are hosted on different origins, set `VITE_API_BASE_URL` to the API origin before building. See `.env.example`. The API host must allow browser requests from the frontend origin.

For example, create a production build with `VITE_API_BASE_URL=https://api.example.org npm run build`.
