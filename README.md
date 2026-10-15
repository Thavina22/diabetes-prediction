# Diabetes Risk Intelligence

> **Live (new):** [diabetes-prediction.vercel.app](https://diabetes-prediction.vercel.app)
> **Live (legacy v1):** [diabetes-prediction-v0.streamlit.app](https://diabetes-prediction-v0.streamlit.app)

A diabetes risk screening platform that combines clinical rules (ADA 2026, AHA-ACC 2025) with a machine learning model (PIMA Random Forest + XGBoost ensemble) to help people understand their health measurements. Built as a **Next.js + FastAPI monorepo** and deployed on **Vercel**.

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
│   │  shadcn/ui, PWA      │        │  /api/python/*       │      │
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
│       │   ├── ml_model.py       # RF + XGBoost + SHAP
│       │   ├── pdf_generator.py  # reportlab
│       │   ├── device_sync.py    # HealthKit/Fit/CGM
│       │   ├── risk_engine.py    # Ensemble + uncertainty
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

| Model | Accuracy | Precision | Recall | F1 |
|-------|----------|-----------|--------|-----|
| Logistic Regression | 70.8% | 60.0% | 50.0% | 0.55 |
| SVM (tuned) | 74.0% | 65.2% | 55.6% | 0.60 |
| **Random Forest (tuned)** | **77.9%** | **71.7%** | **61.1%** | **0.66** |
| **Ensemble (RF + XGB + LR)** | *pending* | *pending* | *pending* | *pending* |

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
# Database (Neon)
DATABASE_URL=postgresql://user:pass@host/db

# Clerk auth
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_ISSUER=https://your-app.clerk.accounts.dev
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...

# Upstash Redis (rate limiting)
UPSTASH_REDIS_REST_URL=https://...
UPSTASH_REDIS_REST_TOKEN=...

# ML model
MODEL_PATH=models/diabetes_rf.joblib
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

### One-time setup

```bash
npm i -g vercel
vercel link                    # link to your Vercel project
```

### Environment variables

Set in Vercel dashboard or via CLI:

```bash
vercel env add DATABASE_URL
vercel env add CLERK_SECRET_KEY
vercel env add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
vercel env add UPSTASH_REDIS_REST_URL
vercel env add UPSTASH_REDIS_REST_TOKEN
```

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
| `POST` | `/api/v1/export/pdf` | Generate clinical PDF |
| `GET` | `/api/v1/history` | List user screenings |
| `GET` | `/api/v1/history/{id}/export?format=fhir` | FHIR R4 export |
| `GET` | `/api/v1/devices` | List connected devices |
| `POST` | `/api/v1/third-party/api-keys` | Create API key |

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
