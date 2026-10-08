# CatScan frontend

React/Vite frontend for the PASJ and JACoW paper validation interfaces. JACoW checkers are implemented; PASJ checkers are placeholders and currently report that validation is unavailable.

## Local development

Run `npm ci` and `npm run start`. The Vite development server proxies `/api` to `http://localhost:8000`, where the FastAPI backend listens by default.

## Production API URL

The frontend uses same-origin `/api` requests by default. When the frontend and API are hosted on different origins, set `VITE_API_BASE_URL` to the API origin before building. See `.env.example`. The API host must allow browser requests from the frontend origin.

For example, create a production build with `VITE_API_BASE_URL=https://api.example.org npm run build`.
