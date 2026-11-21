backend: cd backend && uv run uvicorn catscan.main:app --host 127.0.0.1 --port 3060 --reload
frontend: cd frontend && CATSCAN_API_PROXY_TARGET=http://127.0.0.1:3060 npm run start -- --host 127.0.0.1 --port 3080
