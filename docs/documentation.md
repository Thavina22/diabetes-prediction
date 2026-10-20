# Diabetes Risk Intelligence — Documentation

> **Live:** https://diabetes-prediction-ka8j5q753-thavina-s-projects.vercel.app/  
> **API:** https://diabetes-prediction-api-lemv.onrender.com

This document covers the full architecture, deployment, configuration, and API reference for the diabetes risk screening platform.

---

## 1. Overview

A diabetes risk screening platform that combines clinical rules (ADA 2026, AHA-ACC 2025) with a machine learning model (calibrated soft-voting ensemble — Logistic Regression, SVM, Random Forest, Gradient Boosting and XGBoost over the PIMA dataset).

**Architecture:** Next.js 14 frontend + FastAPI + Python 3.11 backend, deployed as a split service:
- **Frontend:** Next.js on Vercel (free Hobby plan)
- **API:** FastAPI on Render free tier (512 MB Docker container)

> ⚠️ **Screening and education only — not a medical diagnosis.** Always confirm results with a clinician.

---

## 2. Project Structure

```
diabetes-prediction/
├── app/                          # Next.js 14 frontend
│   ├── src/
│   │   ├── app/                  # App Router pages
│   │   ├── components/           # React components
│   │   ├── lib/                  # API client, auth token
│   │   ├── hooks/                # Custom React hooks
│   │   └── types/                # TypeScript types
│   ├── next.config.js            # Vercel rewrite config
│   └── package.json
├── api/
│   └── python/                   # FastAPI backend
│       ├── main.py               # App entry + lifespan
│       ├── config.py             # Pydantic Settings
│       ├── routes/               # API route handlers
│       ├── services/             # Business logic
│       ├── models/               # Pydantic v2 models
│       ├── db/                   # Database layer (asyncpg)
│       └── requirements.txt      # Python dependencies
├── scripts/
│   └── train_ensemble.py         # Model training pipeline
├── data/
│   └── processed/                # Model artifacts (joblib)
├── Dockerfile                    # Single-container build
├── api/python/Dockerfile         # API-only container build
├── docker/entrypoint.sh          # Container entrypoint
├── render.yaml                   # Render Blueprint config
├── docker-compose.yml            # Local Postgres + Redis
├── deploy/oracle/                # Oracle Always-Free VM bootstrap
├── .github/workflows/            # CI/CD pipelines
├── turbo.json                    # Turborepo task pipeline
└── README.md                     # Project README
```

---

## 3. Architecture

### Deployment Shape: Split (Free Tier)

```
┌─────────────────────────────────────────────────────────────┐
│                    Vercel (Frontend, free)                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Next.js 14 + React 18 + Tailwind + shadcn/ui      │   │
│  │  Root Directory: /app                               │   │
│  └──────────────────────┬─────────────────────────────┘   │
│                         │ /api/v1/* rewrite                │
│                         ▼                                  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Render (API, free 512 MB)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  FastAPI + Python 3.11 + uvicorn                    │   │
│  │  scikit-learn + XGBoost (native TreeSHAP)           │   │
│  │  CALIBRATED soft-voting ensemble                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions
- **Same-origin proxying:** Vercel's `next.config.js` rewrites `/api/v1/*` to Render API. Browser stays same-origin — no CORS needed.
- **API fits 512 MB:** Removed `shap`, `pandas`, `numba`, `llvmlite`, `matplotlib` from runtime dependencies. SHAP values computed via XGBoost native `pred_contribs`.
- **Graceful degradation:** If the database is unavailable, screening runs statelessly. If Clerk is missing, auth is bypassed in development mode.

---

## 4. Deployment

### Supported Shapes

| Shape | Frontend | API | Cost | Notes |
|-------|----------|-----|------|-------|
| **Split (recommended)** | Vercel free | Render free (512 MB) | **$0** | Public link, no card |
| **Single container** | Same container | Same container | VM cost | Full control, self-hosted |

### Option A: Split Deployment (Current Live Setup)

**Live URLs:**
- Frontend: https://diabetes-prediction-ka8j5q753-thavina-s-projects.vercel.app/
- API: https://diabetes-prediction-api-lemv.onrender.com

**Steps:**

1. **Deploy API on Render**
   - render.com → Sign up with GitHub → **New +** → **Blueprint**
   - Select repo `sam-black007/diabetes-prediction` → **Apply**
   - `render.yaml` builds `api/python/Dockerfile` as a free Docker web service
   - Wait ~5–10 min, copy the service URL

2. **Deploy frontend on Vercel**
   - vercel.com → Sign up with GitHub → **Add New → Project**
   - Import `sam-black007/diabetes-prediction`
   - **Root Directory → Edit → `app`**
   - **Settings → Environment Variables → Production:**
     - `API_INTERNAL_URL` = `https://<your-render-api>.onrender.com`
   - **Do not** set `NEXT_PUBLIC_API_URL`
   - Click **Deploy**

3. **Verify:**
   - `GET /health` → `{"status":"healthy","version":"2.0.0"}`
   - `POST /api/v1/screening` → returns score + SHAP values

**Gotcha:** Render free sleeps after 15 min idle → first request takes ~1 min (cold start).

### Option B: Single Container (Self-Hosted)

Requires a host with 2 GB RAM.

```bash
# Build
docker build -t diabetes-prediction .

# Run
docker run -p 3000:3000 \
  --env ENVIRONMENT=development \
  --env DEV_AUTH_BYPASS=true \
  diabetes-prediction
# → http://localhost:3000
```

Oracle Cloud Always-Free ARM (4 OCPU / 24 GB) is suitable. See `deploy/oracle/cloud-init.yaml` for bootstrap.

---

## 5. Configuration

### Environment Variables

| Variable | Purpose | Required? |
|----------|---------|-----------|
| `ENVIRONMENT` | `production` enables Clerk/auth; otherwise dev bypass | No |
| `DEV_AUTH_BYPASS` | `true` skips auth in non-production | No |
| `DEV_USER_ID` | Fallback user ID when auth bypassed | No |
| `DATABASE_URL` | Neon Postgres connection string | No (stateless without) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk frontend key | No |
| `CLERK_SECRET_KEY` | Clerk backend key | No |
| `CLERK_ISSUER` | Clerk issuer URL | No |
| `CLERK_WEBHOOK_SECRET` | Svix signature for webhooks | No |
| `API_INTERNAL_URL` | Backend URL for Vercel rewrite (Vercel only) | Yes (split shape) |
| `NEXT_PUBLIC_API_URL` | Leave empty — client is same-origin | No |
| `CRON_SECRET` | Protects device sync cron endpoint | No |
| `UPSTASH_REDIS_REST_URL` | Rate limiting (optional) | No |
| `UPSTASH_REDIS_REST_TOKEN` | Rate limiting token | No |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | No |
| `MODEL_PATH` | Path to model artifacts | No |
| `PORT` | API server port | No (default 8000) |

### Setting Environment Variables on Vercel
```
Settings → Environment Variables → Production
Key: API_INTERNAL_URL
Value: https://<your-render-api>.onrender.com
```

---

## 6. API Reference

All API calls are proxied through Vercel at `/api/v1/*`.

### Screening

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/screening` | Full clinical screening (rules + ML) |
| `GET` | `/api/v1/screening/{id}` | Get stored screening result |

**Request body:**
```json
{
  "age": 54,
  "sex": "M",
  "glucose_mg_dl": 148,
  "sbp": 138,
  "dbp": 86,
  "height_cm": 175,
  "weight_kg": 88,
  "ldl_mg_dl": 142,
  "hdl_mg_dl": 38,
  "triglycerides_mg_dl": 190,
  "family_history": true,
  "pregnancy_status": "none"
}
```

**Response:**
```json
{
  "id": "uuid",
  "user_id": "demo-user",
  "created_at": "2026-10-20T10:00:00Z",
  "input": { ... },
  "glucose_rules": { ... },
  "bp_rule": { ... },
  "bmi_rule": { ... },
  "lipid_rules": { ... },
  "ml_result": {
    "score": 0.473,
    "probability": 0.473,
    "risk_score": 0.473,
    "raw_score": 0.473,
    "calibrated": true,
    "class": 1,
    "threshold": 0.26,
    "uncertainty_low": 0.37,
    "uncertainty_high": 0.97,
    "shap_values": {
      "Pregnancies": 0.080,
      "Glucose": 0.372,
      "BloodPressure": -0.064,
      "SkinThickness": -0.065,
      "Insulin": -0.549,
      "BMI": -0.271,
      "DiabetesPedigreeFunction": 0.048,
      "Age": 0.587
    },
    "shap_base_value": 0.083
  },
  "health_score": 42,
  "risk_category": "very_high",
  "followup_schedule": [ ... ],
  "emergency_flags": [ ... ]
}
```

### Features

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/features` | Effective feature flags |

### Exports

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/export/pdf` | Clinical PDF report |
| `POST` | `/api/v1/export/fhir` | FHIR R4 Bundle |
| `POST` | `/api/v1/export/cda` | HL7 CDA R2 document |

### Third-Party API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/third-party/api-keys` | Create scoped API key |
| `POST` | `/api/v1/third-party/screening` | Screening via API key |
| `GET` | `/api/v1/third-party/history` | History via API key |

**Example:**
```bash
curl -H "Authorization: Bearer drk_live_..." \
  https://<api-url>/api/v1/third-party/screening \
  -d '{"age":54,"sex":"M",...}'
```

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Service health check |

Response: `{"status":"healthy","version":"2.0.0"}`

---

## 7. Model

### Ensemble
- **Soft-voting:** Logistic Regression + SVM + Random Forest + Gradient Boosting + XGBoost
- **Calibration:** Platt sigmoid (`calibrator.joblib`)
- **Conformal interval:** 90% split-conformal (`q ≈ 0.696`)

### SHAP Explanations
Computed via XGBoost native `pred_contribs=True` — exact TreeSHAP values without the `shap` package dependency. Returns 8 PIMA feature contributions in margin (log-odds) space.

### Artifacts
Stored in `api/python/artifacts/`:
- `best_model.joblib` — Gradient Boosting fallback scorer
- `ensemble_model.joblib` — Soft-voting ensemble
- `calibrator.joblib` — Platt sigmoid calibrator
- `scaler.joblib` — Feature scaler
- `ensemble_meta.json` — Metadata (threshold, conformal q, version)

Training: `scripts/train_ensemble.py`

---

## 8. Development

### Local Setup
```bash
# Clone
git clone https://github.com/sam-black007/diabetes-prediction.git
cd diabetes-prediction

# Backend
cd api/python
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd app
npm install
npm run dev
# → http://localhost:3000
```

### Tests
```bash
cd api/python
pip install -r requirements-dev.txt
pytest --cov=services --cov=routes
# 49 tests pass
```

### Lint / Typecheck
```bash
cd app
npm run lint
npm run typecheck
```

---

## 9. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Pydantic v2, uvicorn |
| ML | scikit-learn, XGBoost (native `pred_contribs`) |
| PDF | reportlab (server) |
| Database | Neon Postgres (serverless, optional) |
| Auth | Clerk (optional) |
| Rate Limiting | Upstash Redis (optional) |
| Deploy | Vercel (frontend) + Render (API) |
| CI/CD | GitHub Actions |

---

## 10. Safety

This tool provides **screening and education only — not a medical diagnosis**. Always confirm results with a clinician via fasting glucose / HbA1c test per WHO and IDF guidance.

---

## 11. License

MIT License — free to use, modify, and share.

---
