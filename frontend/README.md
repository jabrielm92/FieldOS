# FieldOS Frontend

This frontend is built with **React + Vite**.

## Scripts
- `npm start` — run Vite dev server
- `npm run build` — production build
- `npm run preview` — preview built output
- `npm test` — run Vitest

## Environment
Copy:
```bash
cp .env.local.example .env.local
```

Set `VITE_BACKEND_URL`:
- Local backend: `http://localhost:8000`
- Same-origin proxy setup: leave blank to use relative `/api/v1`

Set auth persistence mode (optional):
- `VITE_AUTH_PERSIST=session` (default)
- `VITE_AUTH_PERSIST=local`

For full operational setup and deployment notes, see `docs/RUNBOOK.md`.
