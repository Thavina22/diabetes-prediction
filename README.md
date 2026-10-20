# Diabetes Risk Intelligence

> **Live (new):** [diabetes-prediction-ka8j5q753-thavina-s-projects.vercel.app](https://diabetes-prediction-ka8j5q753-thavina-s-projects.vercel.app/)
> **Live (legacy v1):** [diabetes-prediction-v0.streamlit.app](https://diabetes-prediction-v0.streamlit.app)

A diabetes risk screening platform that combines clinical rules (ADA 2026, AHA-ACC 2025) with a machine learning model (a **calibrated soft-voting ensemble** — Logistic Regression, SVM, Random Forest, Gradient Boosting and XGBoost over the PIMA dataset) to help people understand their health measurements. Built as a **Next.js + FastAPI monorepo** and deployable either as **one Docker container** or **split** (Next.js on Vercel, the ML API in a 512 MB container). Hospital and lab systems can pull results through **FHIR R4 / CDA** exports and a **scoped third-party API**.

> ⚠️ **Screening and education only — not a medical diagnosis.** Always confirm results with a clinician.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    One Docker container (one URL)               │
│                                                                 │
│   ┌─────────────────────────┐    ┌──────────────────────┐       │
│   │  Next.js 14 standalone  │ /api/v1/*  FastAPI (Python)      │
│   │  React 18 + Tailwind    │──proxy───►│  uvicorn :8000 │       │
│   │  shadcn/ui, PWA         │    │  (internal)          │       │
│   └──────────┬──────────────┘    └──────────┬───────────┘       │
│              │                              │                   │
│              │ Clerk (auth)                 │ asyncpg           │
│              ▼                              ▼                   │
│      ┌──────────────┐              ┌──────────────────┐         │
│      │  Clerk       │              │  Neon Postgres   │         │
│      │  (10k MAU)   │              │  (0.5 GB free)   │         │
│      └──────────────┘              └──────────────────┘         │
│                                             │                   │
│                                    ┌────────▼────────┐          │
│                                    │ Upstash Redis   │          │
│                                    │ (rate limiting) │          │
│                                    └─────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

The browser only ever talks to the Next.js server. In production `API_BASE_URL` is
same-origin, and `next.config.js` rewrites `/api/v1/:path*` to the internal
FastAPI process, so the API is never exposed directly.

**Cost:** Neon, Clerk and Upstash run on free tiers. The single-container shape needs
**2 GB RAM**; the split shape runs the API comfortably in **512 MB**.

---

## Version History

### v3.0 — Next.js + FastAPI Rewrite (current)
*Single-container monorepo*

- **Next.js 14 frontend** — App Router, React 18, TypeScript strict, Tailwind CSS, shadcn/ui
- **FastAPI backend** — Python 3.11 + uvicorn, same origin behind the Next.js server
- **User accounts & history** — Clerk auth + Neon Postgres persistence
- **Real-time device sync** — Apple HealthKit, Google Fit, CGM (Dexcom/Libre) webhooks
- **Offline PWA** — service worker, IndexedDB queue, background sync
- **Advanced risk modeling** — SHAP explanations, RF+XGBoost ensemble, uncertainty bands
- **Third-party API** — scoped API keys, rate limiting, webhooks
- **FHIR/CDA export** — standards-compliant EHR integration
- **Model retraining** — `scripts/train_ensemble.py` reproduces all artifacts
- **Feature flags** — gradual rollout control

### v2.0 — Advanced Medical Features
*15 new clinical tools*

- A1C ↔ Average Glucose Converter, Risk Stratification, Follow-up Schedule
- Emergency Protocols, Family History, Complication Risks
- Lifestyle Recommendations, Medication Impacts, Comorbidity Assessment
- What-If Simulator, Gestational Diabetes, Pediatric/Elderly Adjustments
- Previous Report Comparison, Risk Factor Breakdown

### v1.5 — Unit Converter & Dark Mode
### v1.4 — Health Score & Sharing
### v1.3 — AI & Accessibility
### v1.2 — Clinical Accuracy
### v1.1 — UI/UX Overhaul
### v1.0 — Core Screening Engine

---

## Project Structure

```
diabetes-prediction/
├── app/                          # Next.js 14 frontend
│   ├── src/
│   │   ├── app/                  # App Router pages
│   │   │   ├── (auth)/           # Landing + auth pages
│   │   │   ├── (dashboard)/      # Protected app routes
│   │   │   │   ├── screening/    # 3-step health check
│   │   │   │   ├── history/      # Paginated history + detail
│   │   │   │   ├── devices/      # Device connections
│   │   │   │   ├── settings/     # Preferences + API keys
│   │   │   │   └── api-docs/     # Third-party API reference
│   │   │   ├── api/              # Next.js API routes (proxy)
│   │   │   ├── layout.tsx        # Root layout
│   │   │   └── globals.css       # Tailwind + medical palette
│   │   ├── components/
│   │   │   ├── ui/               # shadcn/ui primitives
│   │   │   ├── screening/        # Screening components
│   │   │   ├── charts/           # Recharts wrappers
│   │   │   └── pdf/              # @react-pdf/renderer
│   │   ├── lib/                  # api client, auth token, validation/
│   │   ├── hooks/                # Custom React hooks
│   │   ├── store/                # Zustand (offline, UI)
│   │   └── types/                # OpenAPI-generated types
│   ├── next.config.js            # next-pwa config
│   └── tailwind.config.ts
│
├── api/
│   └── python/                   # FastAPI backend
│       ├── main.py               # App entry + lifespan
│       ├── config.py             # Pydantic Settings
│       ├── routes/
│       │   ├── screening.py      # POST /screening
│       │   ├── health_score.py   # POST /health-score
│       │   ├── ml_inference.py   # POST /ml/predict
│       │   ├── pdf_export.py     # POST /export/pdf
│       │   ├── history.py        # GET /history
│       │   ├── devices.py        # Device webhooks + sync
│       │   └── third_party.py    # API keys + rate limits
│       ├── models/               # Pydantic v2 models
│       ├── services/
│       │   ├── clinical_rules.py # Clinical engine (pure Python)
│       │   ├── ml_model.py       # Ensemble + calibration + SHAP
│       │   ├── pdf_generator.py  # reportlab
│       │   ├── device_sync.py    # HealthKit/Fit/CGM
│       │   ├── screening_engine.py # Result assembler (build_result)
│       │   ├── feature_flags.py  # Flags + percentage rollout
│       │   ├── rate_limit.py     # Upstash / in-memory limiter
│       │   └── fhir_export.py    # FHIR R4 / CDA
│       ├── db/
│       │   ├── connection.py     # asyncpg pool
│       │   ├── migrations/       # Alembic
│       │   └── repositories/
│       ├── auth/clerk.py         # JWT verification
│       └── requirements.txt
│
├── packages/
│   └── shared-types/             # OpenAPI → TypeScript
│
├── .github/workflows/
│   ├── ci.yml                    # v3 monorepo: frontend + backend pytest
│   └── test.yml                  # legacy v1 pipeline (preprocessing → training)
│
├── docs/superpowers/specs/       # Design specs
├── .Codex/plans/                 # Implementation plans
├── docker-compose.yml            # Local Postgres + Redis
├── Dockerfile                    # Single-image build (Next.js + FastAPI)
├── docker/entrypoint.sh          # Starts uvicorn + Next.js in one container
├── deploy/oracle/                # Always-free VM bootstrap + cloud-init
├── render.yaml                   # Render blueprint (API-only service)
├── turbo.json                    # Turborepo task pipeline
└── package.json                  # Root workspace
```

> The repository root also still hosts the **legacy v1 Streamlit app** (`app.py`,
> `src/`, `tests/`, root `requirements.txt`), deployed separately. The v3
> architecture above lives in `app/` and `api/`.

---

## Clinical Rules Engine

Every verdict comes from a single, transparent, offline rules layer (`api/python/services/clinical_rules.py`), not from the LLM.

- **Glucose** — measurement-type aware (fasting, post-meal, HbA1c, OGTT, random) with ADA 2026 thresholds
- **Blood pressure** — independent SBP/DBP OR-logic (AHA/ACC 2025)
- **BMI** — computed from height + weight
- **Lipids** — LDL-C, HDL-C, triglycerides scored independently
- **Red-flag engine** — glucose 400+, BP emergency + symptoms surfaced first

---

## ML Model Accuracy

> **Deployed model:** a **soft-voting ensemble** (Logistic Regression, SVM, Random
> Forest, Gradient Boosting, XGBoost) trained on the PIMA Indians Diabetes
> Database (768 records, 8 features) and shipped as
> `data/processed/ensemble_model.joblib`. Raw scores are **Platt-calibrated**
> (`calibrator.joblib`) and paired with **split-conformal 90% intervals**
> (`conformal_q ≈ 0.70`). Tree-SHAP explanations come from the ensemble's XGBoost
> member via its native `pred_contribs` (no `shap` dependency). All artifacts are
> produced by `scripts/train_ensemble.py`. It outputs a supplementary risk score
> only — the clinical rules engine remains the source of truth.

| Model | F1 | AUC | Notes |
|-------|----|-----|-------|
| Gradient Boosting (baseline) | 0.592 | 0.823 | fallback scorer if the ensemble is missing |
| **Soft-voting ensemble** | **0.681** | **0.825** | decision threshold 0.26 |
| **+ Platt calibration (deployed)** | **0.727** | **0.825** | calibrated probability |
| Conformal interval (90%) | — | — | `q = 0.696`, test coverage 0.883 |

---

## How to Run

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker (for local Postgres + Redis)

### 1. Install dependencies

```bash
npm install                    # installs all workspaces
cd api/python && pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Required variables:

```bash
# Database (Neon) — leave blank to run in stateless mode
DATABASE_URL=postgresql://user:pass@host/db

# Clerk auth — leave blank locally to run without auth
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_ISSUER=https://your-app.clerk.accounts.dev
CLERK_WEBHOOK_SECRET=whsec_...        # POST /api/v1/webhooks/clerk (Svix)

# Upstash Redis (rate limiting) — optional, falls back to in-memory
UPSTASH_REDIS_REST_URL=https://...
UPSTASH_REDIS_REST_TOKEN=...

# Cron protection — your scheduler sends `Authorization: Bearer <CRON_SECRET>`
CRON_SECRET=

# Local-only auth bypass (never enable in production)
DEV_AUTH_BYPASS=false
DEV_USER_ID=dev-user

# Frontend -> API base URL (local dev only; production uses same-origin)
NEXT_PUBLIC_API_URL=http://localhost:8000

# ML model directory
MODEL_PATH=data/processed/best_model.joblib
```

### 3. Start local services

```bash
docker-compose up -d           # Postgres + Redis
```

### 4. Run migrations

```bash
cd api/python
alembic upgrade head
```

### 5. Start dev servers

```bash
# Terminal 1 — FastAPI
cd api/python && uvicorn main:app --reload --port 8000

# Terminal 2 — Next.js
cd app && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) (frontend) or [http://localhost:8000/docs](http://localhost:8000/docs) (API).

---

## Deployment

Two supported shapes:

| Shape | Frontend | API | Cost | Use when |
|-------|----------|-----|------|----------|
| **Split** | Vercel (free, no card) | Render free (512 MB, no card) | **$0** | You want a public link with no credit card |
| **Single container** | same container | same container | VM cost | You want one host / full control |

### Split: Vercel (frontend) + Render (ML API)

The frontend runs on Vercel's free Hobby plan and the FastAPI + ML stack runs in a
512 MB Render container. Vercel's `next.config.js` rewrite proxies `/api/v1/*` to the
API, so the browser stays same-origin and no CORS is needed.

**Live demo:** https://diabetes-prediction-ka8j5q753-thavina-s-projects.vercel.app/  
**API:** `https://diabetes-prediction-api-lemv.onrender.com` (deployed on Render free tier)

1. **Deploy the API first.** Render → **New +** → **Blueprint** → pick this repo.
   `render.yaml` builds `api/python/Dockerfile` as a free Docker web service.
   Copy the resulting URL, e.g. `https://diabetes-prediction-api-lemv.onrender.com`.
2. **Deploy the frontend.** Import the repo on Vercel and set the project's
   **Root Directory to `app/`** (Framework preset: Next.js).
3. Add the API URL as a Vercel environment variable and redeploy:

   ```bash
   API_INTERNAL_URL=https://<your-api>.onrender.com
   ```

   Do **not** set `NEXT_PUBLIC_API_URL` — leaving it empty keeps the client
   same-origin so every call goes through the rewrite.

Notes: the free API sleeps after 15 minutes idle (~1 minute cold start), and
`ENVIRONMENT=development` + `DEV_AUTH_BYPASS=true` run it without Clerk or a database.
Add a free Neon Postgres and Clerk keys to enable accounts, history and API keys.

### Single container (one host)

The root `Dockerfile` builds one image containing both: Next.js in standalone mode
plus Python 3.11 running FastAPI beside it, with `docker/entrypoint.sh` starting
both and Next.js as the only public server.

```bash
# Build and run locally (needs Docker)
docker build -t diabetes-prediction .
docker run -p 3000:3000 --env ENVIRONMENT=development --env DEV_AUTH_BYPASS=true diabetes-prediction
# → http://localhost:3000
```

#### Deploy to Oracle Cloud (always free, 24 GB)

Oracle's Always Free ARM shape (`VM.Standard.A1.Flex`, 4 OCPU / 24 GB) comfortably
runs the whole stack and is free with no time limit. It is a normal always-on VM —
your laptop is only used for setup.

1. Create an instance: **Ubuntu 22.04/24.04**, shape **`VM.Standard.A1.Flex`**
   (4 OCPU, 24 GB), add your SSH key, and paste `deploy/oracle/cloud-init.yaml`
   into *Advanced options → Management → Cloud-init script*.
2. In the VCN's **security list**, add an ingress rule: source `0.0.0.0/0`,
   TCP, destination port **3000**.
3. Wait for the build (a few minutes), then open `http://<public-ip>:3000`.

To update later, SSH in and re-run the bootstrap (it re-pulls and rebuilds):

```bash
ssh ubuntu@<public-ip> 'APP_DIR=/home/ubuntu/app bash /home/ubuntu/app/deploy/oracle/bootstrap.sh'
```

Put real secrets in `/home/ubuntu/app/.env.production` — the bootstrap passes it to
the container automatically. For HTTPS, put Caddy or nginx in front of port 3000.

> **Why isn't the API on Vercel?** Vercel's Python functions cap the bundle at
> 500 MB. The scikit-learn + XGBoost stack unpacks to roughly 1 GB, so it cannot
> run as a serverless function — but it fits a 512 MB container on its own.

**Other hosts:** any Docker host works. Railway, Fly.io, Hetzner and DigitalOcean all
accept the root `Dockerfile` unchanged; point them at it and give the container 2 GB.
`api/python/Dockerfile` is the API-only variant used by the split deployment.

### Environment variables

Set on the host (all optional for a no-database demo):

| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT` | `production` for real auth; anything else enables the dev bypass below |
| `DEV_AUTH_BYPASS` | `true` runs without Clerk/DB (demo only; ignored when `ENVIRONMENT=production`) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk publishable key — **inlined at build time**, pass as a Docker build arg |
| `NEXT_PUBLIC_API_URL` | Leave empty/`""` in the container — the client is same-origin |
| `DATABASE_URL` | Neon Postgres (enables history, devices, API keys) |
| `CLERK_SECRET_KEY`, `CLERK_ISSUER` | Clerk JWT verification |
| `CLERK_WEBHOOK_SECRET` | Svix signature for `POST /api/v1/webhooks/clerk` |
| `CRON_SECRET` | Protects `GET|POST /api/v1/cron/sync-devices` |
| `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` | Distributed rate limiting |
| `CORS_ORIGINS` | JSON array, only needed if the API is called cross-origin |

- **Python 3.11** is pinned in `api/python/.python-version` and the image is built on
  Debian bookworm (Python 3.11), matching the interpreter the model artifacts were
  pickled with.
- Scheduling `sync-devices` is host-specific (e.g. a Render cron job hitting
  `/api/v1/cron/sync-devices` with the `CRON_SECRET`).

---

## API Reference

Auto-generated OpenAPI docs:

- **Local:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Production:** `https://<your-app-domain>/api-docs`

### Core endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/screening` | Run full clinical screening |
| `GET` | `/api/v1/screening/{id}` | Get screening result |
| `POST` | `/api/v1/health-score` | Calculate 0-100 score |
| `POST` | `/api/v1/ml/predict` | ML inference + SHAP |
| `POST` | `/api/v1/ml/predict-simple` | ML inference without SHAP |
| `POST` | `/api/v1/export/pdf` | Generate a clinical PDF (stateless) |
| `POST` | `/api/v1/export/fhir` | FHIR R4 Bundle (stateless) |
| `POST` | `/api/v1/export/cda` | HL7 CDA R2 document (stateless) |
| `GET` | `/api/v1/history` | List user screenings |
| `GET` | `/api/v1/history/{id}/export?format=pdf\|fhir\|cda` | Export a stored screening |
| `GET` | `/api/v1/devices` | List connected devices |
| `GET` | `/api/v1/features` | Effective feature flags |
| `POST` | `/api/v1/third-party/api-keys` | Create API key |
| `POST` | `/api/v1/third-party/screening` | Screening via API key (scope `screening:write`) |
| `GET` | `/api/v1/third-party/history` | History via API key (scope `history:read`) |
| `GET/POST` | `/api/v1/cron/sync-devices` | Background device sync (cron) |
| `POST` | `/api/v1/webhooks/clerk` | Clerk user sync (Svix-verified) |

### Third-party authentication

```bash
curl -H "Authorization: Bearer drk_live_..." \
  https://<your-app-domain>/api/v1/third-party/history
```

---

## Testing

```bash
# Backend — pytest + coverage (49 tests)
cd api/python
pip install -r requirements-dev.txt
pytest --cov=services --cov=routes

# Frontend — quality gates
cd app
npm run lint
npm run typecheck
```

CI (`.github/workflows/ci.yml`) runs both on every push and PR to `main`.
Frontend unit (`vitest`) and E2E (`playwright`) suites are wired in
`app/package.json` but do not yet have test files, so they are not in CI.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn/ui |
| State | TanStack Query (server), Zustand (client) |
| Forms | React Hook Form + Zod |
| Backend | FastAPI, Pydantic v2, asyncpg |
| Database | Neon Postgres (serverless) |
| Auth | Clerk |
| Rate limiting | Upstash Redis |
| ML | scikit-learn, XGBoost (native tree-SHAP) |
| PDF | reportlab (server), @react-pdf/renderer (client) |
| PWA | next-pwa (Workbox), idb |
| Deploy | Docker (single container; Render blueprint included) |
| CI/CD | GitHub Actions (`.github/workflows/ci.yml`) |

---

## Safety

This tool provides **screening and education only — not a medical diagnosis**. Always confirm results with a clinician via fasting glucose / HbA1c test per WHO and IDF guidance.

---

## License

MIT License — free to use, modify, and share.
