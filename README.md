# Shongkhep AI v2 🇧🇩

> **Production-grade AI summarization SaaS** — Bangla + English  
> FastAPI · PostgreSQL · Redis · Celery · Prometheus · Grafana · Next.js 14

---

## What's new in v2

| Feature | Details |
|---|---|
| **Redis cache** | SHA-256 keyed summary cache — identical requests return instantly, no inference |
| **Celery async queue** | `POST /summarize/async` offloads mT5 inference to worker processes |
| **GPU / Accelerate** | `device_map="auto"` routes model to CUDA/MPS/CPU automatically |
| **Prometheus metrics** | Inference latency histogram, cache hit/miss, plan gauges — at `/metrics` |
| **Grafana dashboard** | Pre-provisioned dashboard auto-loads on `docker compose up` |
| **Webhook system** | HMAC-signed event delivery via Celery (summarize.complete, limit.reached, limit.warning) |
| **Admin router** | Platform stats, user management, plan overrides — JWT-protected |
| **Flower monitor** | Celery task queue UI at http://localhost:5555 |
| **Improved DB pooling** | `pool_recycle=1800`, `pool_timeout=30`, configurable pool size |

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │           docker-compose             │
                    │                                      │
  Browser ──────────► Next.js :3000                        │
                    │     │                                │
                    │     ▼                                │
                    │  FastAPI :8000 ◄── Prometheus :9090  │
                    │     │    │              │            │
                    │     │    └──► Redis :6379 ◄──────────┤
                    │     │              │                 │
                    │     ▼              ▼                 │
                    │  PostgreSQL   Celery Worker          │
                    │  :5432        (mT5 inference)        │
                    │                   │                  │
                    │              Flower :5555            │
                    │                                      │
                    │  Grafana :3001 ◄── Prometheus        │
                    └─────────────────────────────────────┘
```

---

## Quick start (Docker — recommended)

```bash
git clone <repo>
cd shongkhep

# Copy env and change SECRET_KEY at minimum
cp backend/.env.example backend/.env

# Start everything
docker compose up --build

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

| Service | URL | Credentials |
|---|---|---|
| Frontend | http://localhost:3000 | — |
| API + Swagger | http://localhost:8000/docs | — |
| Grafana | http://localhost:3001 | admin / grafanapass |
| Flower (Celery) | http://localhost:5555 | admin / flowerpass |
| Prometheus | http://localhost:9090 | — |

> First startup downloads the mT5 model (~300 MB). Cached in a Docker volume — instant on restart.

---

## Local dev (no Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL + REDIS_URL

# Postgres + Redis must be running locally
createdb shongkhep_db

# API server
uvicorn app.main:app --reload --port 8000

# Celery worker (separate terminal)
celery -A app.worker worker --loglevel=info --concurrency=2 -Q summarize,webhooks
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

---

## API Reference

### Sync summarize
```http
POST /api/v1/summarize
X-API-Key: sk-...

{ "text": "...", "language": "auto" }
```
Checks Redis cache first. Cache TTL: 1 hour.

### Async summarize
```http
POST /api/v1/summarize/async        → 202 { "job_id": "abc..." }
GET  /api/v1/summarize/jobs/{id}    → { "status": "SUCCESS", "result": {...} }
```
Offloads to Celery. Poll every ~1.5s until `status === "SUCCESS"`.

### Webhooks
```http
POST   /api/v1/webhooks          Create endpoint
GET    /api/v1/webhooks          List endpoints
DELETE /api/v1/webhooks/{id}     Remove
POST   /api/v1/webhooks/{id}/test  Send test ping
```
Verify delivery with header: `X-Shongkhep-Signature: sha256=<hmac>`

### Admin (admin accounts only)
```http
GET  /api/v1/admin/stats
GET  /api/v1/admin/users
POST /api/v1/admin/users/{id}/plan
POST /api/v1/admin/users/{id}/deactivate
POST /api/v1/admin/users/{id}/reset-usage
```

---

## Environment variables

See `backend/.env.example` for the full list. Key additions in v2:

| Variable | Default | Purpose |
|---|---|---|
| `REDIS_URL` | redis://localhost:6379/0 | Cache + rate limit backing |
| `CELERY_BROKER_URL` | redis://...6379/1 | Task broker |
| `CELERY_RESULT_BACKEND` | redis://...6379/2 | Job result store |
| `MODEL_DEVICE` | auto | `auto`/`cpu`/`cuda`/`mps` |
| `MODEL_TORCH_DTYPE` | auto | `auto`/`float16`/`float32` |
| `ENABLE_METRICS` | true | Toggle Prometheus endpoint |
| `WEBHOOK_MAX_RETRIES` | 3 | Retry count for failed deliveries |
| `ADMIN_SECRET` | changeme | Extra admin route protection |

---

## Plans

| Plan | Requests/mo | Price BDT |
|---|---|---|
| Free | 100 | ৳0 |
| Basic | 2,000 | ৳499 |
| Pro | 10,000 | ৳1,499 |

---

## Scaling checklist

- [x] Redis caching layer
- [x] Celery async inference workers
- [x] GPU device routing (Accelerate)
- [x] Prometheus + Grafana observability
- [x] Webhook system with HMAC signing
- [x] Admin API with user management
- [x] Connection pool tuning
- [ ] Alembic versioned migrations (replace `create_all`)
- [ ] Horizontal Celery workers behind a load balancer
- [ ] SSLCommerz / bKash payment integration
- [ ] Fine-tune mT5 on Bangla news corpora (Prothom Alo, Daily Star BD)
- [ ] Multi-region deployment (AWS ap-southeast-1 for Bangladesh latency)

---

Made with ❤️ for Bangladesh 🇧🇩 — v2.0.0
