# FieldOS Runbook

This is the canonical operational runbook for local development, CI checks, and deployment wiring.

## Services
- Backend API: FastAPI (`backend/app.py`)
- Frontend app: React + Vite (`frontend/`)
- Data stores: MongoDB + Redis
- Workers: Celery worker for async jobs

## Environment

### Backend (`backend/.env`)
Required:
- `MONGO_URL`
- `DB_NAME`
- `JWT_SECRET` (must be set; production should be 32+ chars)

Common integrations:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_MESSAGING_SERVICE_SID`
- `OPENAI_API_KEY`
- `ELEVENLABS_API_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `RESEND_API_KEY`

Security/runtime:
- `ENVIRONMENT=development|production`
- `CORS_ORIGINS=http://localhost:3000,http://localhost`
- `REDIS_URL`
- `DEFAULT_SUPERADMIN_EMAIL` / `DEFAULT_SUPERADMIN_PASSWORD` (optional bootstrap only)

### Frontend (`frontend/.env.local`)
- `VITE_BACKEND_URL` (optional; if empty, frontend calls `/api/v1` same-origin)
- `VITE_AUTH_PERSIST=session|local` (defaults to `session`)

## Local Development

### Docker stack (recommended)
```bash
docker compose up --build
```

### Backend only
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Frontend only
```bash
cd frontend
npm ci
npm start
```

## Validation

### Python tests
```bash
pytest
```

### Frontend build
```bash
cd frontend
npm run build
```

### Python syntax sanity
```bash
python -m py_compile backend/app.py backend/core/config.py backend/core/lifecycle.py
```

## CI
GitHub Actions workflow:
- backend dependency install + `pytest`
- frontend dependency install + `npm run build`

File: `.github/workflows/ci.yml`

## Legacy and historical docs
- `requirements.md` is now historical product context and changelog notes.
- root-level smoke tests were moved to `scripts/smoke/`.
