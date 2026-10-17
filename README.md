# Diabetes Risk Intelligence

> **Live (new):** [diabetes-prediction.vercel.app](https://diabetes-prediction.vercel.app)
> **Live (legacy v1):** [diabetes-prediction-v0.streamlit.app](https://diabetes-prediction-v0.streamlit.app)

A diabetes risk screening platform that combines clinical rules (ADA 2026, AHA-ACC 2025) with a machine learning model (a **calibrated soft-voting ensemble** — Logistic Regression, SVM, Random Forest, Gradient Boosting and XGBoost over the PIMA dataset) to help people understand their health measurements. Built as a **Next.js + FastAPI monorepo** and deployed on **Vercel**. Hospital and lab systems can pull results through **FHIR R4 / CDA** exports and a **scoped third-party API**.

> ⚠️ **Screening and education only — not a medical diagnosis.** Always confirm results with a clinician.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Vercel (single deploy)                 │
│                                                                 │
│   ┌──────────────────────┐        ┌──────────────────────┐      │
│   │  Next.js 14 (App)    │  HTTPS │  FastAPI (Python)    │      │
│   │  React 18 + Tailwind │◄──────►│  Serverless Functions│      │
│   │  shadcn/ui, PWA      │        │  /api/v1/*           │      │
│   └──────────┬───────────┘        └──────────┬───────────┘      │
│              │                               │                  │
│              │ Clerk (auth)                  │ asyncpg          │
│              ▼                               ▼                  │
│      ┌──────────────┐               ┌──────────────────┐        │
│      │  Clerk       │               │  Neon Postgres   │        │
│      │  (10k MAU)   │               │  (0.5 GB free)   │        │
│      └──────────────┘               └──────────────────┘        │
│                                              │                  │
│                                     ┌────────▼────────┐         │
│                                     │ Upstash Redis   │         │
│                                     │ (rate limiting) │         │
│                                     └─────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

**Total cost: $0/month** on free tiers (Vercel Hobby, Neon, Clerk, Upstash).

---

## Version History

### v3.0 — Vercel Rewrite (current)
*Next.js + FastAPI monorepo*

- **Next.js 14 frontend** — App Router, React 18, TypeScript strict, Tailwind CSS, shadcn/ui
- **FastAPI backend** — Python serverless functions on Vercel
- **User accounts & history** — Clerk auth + Neon Postgres persistence
- **Real-time device sync** — Apple HealthKit, Google Fit, CGM (Dexcom/Libre) webhooks
- **Offline PWA** — service worker, IndexedDB queue, background sync
- **Advanced risk modeling** — SHAP explanations, RF+XGBoost ensemble, uncertainty bands
- **Third-party API** — scoped API keys, rate limiting, webhooks
- **FHIR/CDA export** — standards-compliant EHR integration
- **Automated retraining** — weekly GitHub Action pipeline
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
│   │   ├── lib/                  # api.ts, auth.ts, validation/
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
│   ├── ci.yml                    # lint, typecheck, test, build
│   ├── deploy-preview.yml        # Vercel preview on PR
│   └── deploy-prod.yml           # Vercel prod on merge
│
├── docs/superpowers/specs/       # Design specs
├── .Codex/plans/                 # Implementation plans
├── docker-compose.yml            # Local Postgres + Redis
├── turbo.json                    # Turborepo pipeline
├── vercel.json                   # Vercel config
└── package.json                  # Root workspace
```

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
> (`conformal_q ≈ 0.70`). SHAP explanations come from the Gradient Boosting
> member (`best_model.joblib`). All artifacts are produced by
> `scripts/train_ensemble.py`. It outputs a supplementary risk score only — the
> clinical rules engine remains the source of truth.

| Model | F1 | AUC | Notes |
|-------|----|-----|-------|
| Gradient Boosting (baseline) | 0.592 | 0.823 | SHAP explainer member |
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

# Cron protection — Vercel sends `Authorization: Bearer <CRON_SECRET>`
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

## Deployment (Vercel)

The project deploys as **one Vercel project using [Services](https://vercel.com/docs/services)**: a `web` service (Next.js, `app/`) and an `api` service (FastAPI, `api/python/`). Repo-root `vercel.json` declares both services and the rewrites that publish them — `/api/v1/*` → `api`, everything else → `web`. Rewrites preserve the path, so FastAPI sees its own `/api/v1/...` routes.

> **Note:** Without this config, Vercel would serve the Python entrypoint at its *file path* (`/api/python/main`) and never forward `/api/v1/*`, so the frontend would get 404s. Services (beta) is the documented way to run a Next.js frontend and a Python backend in one repo.

### One-time setup

```bash
npm i -g vercel
vercel link                    # link to your Vercel project
```

### Environment variables

Set in the Vercel dashboard (or via `vercel env add`):

```bash
vercel env add DATABASE_URL
vercel env add CLERK_SECRET_KEY
vercel env add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
vercel env add CLERK_WEBHOOK_SECRET
vercel env add CRON_SECRET
vercel env add UPSTASH_REDIS_REST_URL
vercel env add UPSTASH_REDIS_REST_TOKEN
vercel env add CORS_ORIGINS            # e.g. ["https://<your-domain>"]
vercel env add ENVIRONMENT             # production
vercel env add PYTHON_VERSION          # 3.11 (matches the ML artifacts)
```

- **`ENVIRONMENT`** must not be `development`, so `DEV_AUTH_BYPASS` is ignored.
- **`PYTHON_VERSION=3.11`** matches the interpreter the model artifacts were pickled with. If you bump the runtime, re-run `scripts/train_ensemble.py` there.
- **`NEXT_PUBLIC_API_URL`** can be left unset in production — the client falls back to same-origin and calls `/api/v1/*`.

### Cron

`vercel.json` schedules `GET /api/v1/cron/sync-devices` daily (`0 6 * * *`). Set `CRON_SECRET` and Vercel sends it automatically as `Authorization: Bearer <secret>`; the route returns 401 without it when the secret is configured.

### Deploy

```bash
vercel                         # preview deploy
vercel --prod                  # production deploy
```

CI/CD is automated: PRs get preview deploys, merges to `main` deploy to production.

---

## API Reference

Auto-generated OpenAPI docs:

- **Local:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Production:** [https://diabetes-prediction.vercel.app/api-docs](https://diabetes-prediction.vercel.app/api-docs)

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
  https://diabetes-prediction.vercel.app/api/v1/third-party/history
```

---

## Testing

```bash
# Backend
cd api/python
pytest tests/ -v --cov=services

# Frontend
cd app
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

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
| ML | scikit-learn, XGBoost, SHAP |
| PDF | reportlab (server), @react-pdf/renderer (client) |
| PWA | next-pwa (Workbox), idb |
| Deploy | Vercel (Hobby) |
| CI/CD | GitHub Actions |

---

## Safety

This tool provides **screening and education only — not a medical diagnosis**. Always confirm results with a clinician via fasting glucose / HbA1c test per WHO and IDF guidance.

---

## License

MIT License — free to use, modify, and share.
