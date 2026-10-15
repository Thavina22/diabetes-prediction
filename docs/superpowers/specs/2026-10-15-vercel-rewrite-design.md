# Diabetes Risk Intelligence — Vercel Rewrite Design

**Date**: 2026-10-15
**Status**: Approved
**Repo**: sam-black007/diabetes-prediction

---

## 1. Project Structure (Monorepo)

```
diabetes-prediction/
├── app/                          # Next.js 14+ App Router frontend
│   ├── src/
│   │   ├── app/                  # App Router pages & layouts
│   │   │   ├── (auth)/           # Auth group (sign-in, sign-up)
│   │   │   ├── (dashboard)/      # Protected dashboard routes
│   │   │   │   ├── screening/    # Health check flow
│   │   │   │   ├── history/      # Past screenings
│   │   │   │   ├── devices/      # Device connections
│   │   │   │   ├── settings/     # User preferences
│   │   │   │   └── api-docs/     # Third-party API docs
│   │   │   ├── api/              # Next.js API routes (proxy to FastAPI)
│   │   │   └── layout.tsx
│   │   ├── components/           # Shared React components
│   │   │   ├── ui/               # shadcn/ui primitives
│   │   │   ├── screening/        # Screening-specific components
│   │   │   ├── charts/           # Recharts wrappers
│   │   │   └── pdf/              # @react-pdf/renderer components
│   │   ├── lib/                  # Utilities, configs
│   │   │   ├── api.ts            # TanStack Query + Axios client
│   │   │   ├── auth.ts           # Clerk helpers
│   │   │   ├── validation/       # Zod schemas (mirror Pydantic)
│   │   │   └── pwa.ts            # Service worker registration
│   │   ├── hooks/                # Custom React hooks
│   │   ├── store/                # Zustand stores (offline queue, UI state)
│   │   └── types/                # Generated from OpenAPI
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
│
├── api/
│   └── python/                   # FastAPI backend (Vercel Python functions)
│       ├── main.py               # FastAPI app entry
│       ├── routes/
│       │   ├── screening.py      # POST /screening, GET /screening/{id}
│       │   ├── health_score.py   # POST /health-score
│       │   ├── ml_inference.py   # POST /ml/predict
│       │   ├── pdf_export.py     # POST /export/pdf
│       │   ├── history.py        # GET /history, GET /history/{id}
│       │   ├── devices.py        # Device webhooks, sync
│       │   └── third_party.py    # API keys, rate limits, webhooks
│       ├── models/
│       │   ├── screening.py      # Pydantic v2 models
│       │   ├── user.py
│       │   ├── device.py
│       │   └── api_key.py
│       ├── services/
│       │   ├── clinical_rules.py # Ported from src/clinical_rules.py
│       │   ├── ml_model.py       # Model loading, inference
│       │   ├── pdf_generator.py  # reportlab port
│       │   ├── device_sync.py    # Apple HealthKit, Google Fit, CGM
│       │   └── risk_engine.py    # Advanced risk (SHAP, ensemble)
│       ├── db/
│       │   ├── connection.py     # Neon Postgres (asyncpg)
│       │   ├── migrations/       # Alembic migrations
│       │   └── repositories/     # Data access layer
│       ├── auth/
│       │   └── clerk.py          # Clerk JWT verification
│       ├── config.py             # Pydantic Settings
│       └── requirements.txt
│
├── packages/
│   └── shared-types/             # Generated TypeScript types from OpenAPI
│       ├── package.json
│       └── src/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                # Lint, typecheck, test, build
│       ├── deploy-preview.yml    # Vercel preview on PR
│       └── deploy-prod.yml       # Vercel production on merge
│
├── docs/
│   └── superpowers/specs/        # This file
│
├── docker-compose.yml            # Local dev (Postgres, Redis)
├── turbo.json                    # Turborepo config (optional)
├── package.json                  # Root workspace scripts
└── README.md
```

---

## 2. API Design (FastAPI + Pydantic v2)

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/screening` | Run full clinical screening |
| `GET` | `/api/v1/screening/{id}` | Get screening result |
| `POST` | `/api/v1/health-score` | Calculate 0-100 health score |
| `POST` | `/api/v1/ml/predict` | ML model inference |
| `POST` | `/api/v1/export/pdf` | Generate clinical PDF |
| `GET` | `/api/v1/history` | List user screenings (paginated) |
| `GET` | `/api/v1/history/{id}` | Get single screening |
| `POST` | `/api/v1/devices/webhook/apple-health` | Apple HealthKit webhook |
| `POST` | `/api/v1/devices/webhook/google-fit` | Google Fit webhook |
| `POST` | `/api/v1/devices/webhook/cgm` | CGM device webhook |
| `GET` | `/api/v1/third-party/api-keys` | List user API keys |
| `POST` | `/api/v1/third-party/api-keys` | Create API key |
| `DELETE` | `/api/v1/third-party/api-keys/{id}` | Revoke API key |

### Key Pydantic Models

```python
# Screening input (mirrors current app.py intake)
class ScreeningInput(BaseModel):
    glucose_mg_dl: Optional[float] = None
    glucose_type: Literal["fasting", "postprandial", "random", "hba1c", "ogtt"] = "fasting"
    sbp: Optional[int] = None
    dbp: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    ldl_mg_dl: Optional[float] = None
    hdl_mg_dl: Optional[float] = None
    triglycerides_mg_dl: Optional[float] = None
    age: Optional[int] = None
    sex: Optional[Literal["M", "F"]] = None
    family_history: bool = False
    medications: List[str] = []
    comorbidities: List[str] = []
    pregnancy_status: Optional[Literal["none", "gestational", "preexisting"]] = None
    unit_preference: Literal["mg_dL", "mmol_L"] = "mg_dL"

# Screening output
class ScreeningResult(BaseModel):
    id: UUID
    user_id: str
    created_at: datetime
    input: ScreeningInput
    glucose_rules: List[ClinicalRule]
    bp_rule: ClinicalRule
    bmi_rule: ClinicalRule
    lipid_rules: List[ClinicalRule]
    ml_result: MLResult
    health_score: int
    risk_category: Literal["low", "medium", "high", "very_high"]
    followup_schedule: FollowupSchedule
    emergency_flags: List[EmergencyFlag]
    shap_explanation: Optional[SHAPExplanation] = None
```

### OpenAPI → TypeScript Generation

```bash
# In CI: generate types after FastAPI builds
cd api/python && python -c "from main import app; import json; print(json.dumps(app.openapi()))" > openapi.json
npx openapi-typescript openapi.json -o ../../packages/shared-types/src/api.d.ts
```

---

## 3. Authentication & Database

### Auth: Clerk

- **Providers**: Email/password, Google, GitHub, Microsoft
- **Session**: JWT in HttpOnly cookie (Clerk handles)
- **Middleware**: `clerkMiddleware()` protects `/dashboard/*` routes
- **User sync**: Clerk webhook → Neon `users` table on `user.created`

### Database: Neon Postgres (via Vercel Postgres)

```sql
-- Users (synced from Clerk)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    unit_preference TEXT DEFAULT 'mg_dL',
    theme TEXT DEFAULT 'system',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Screenings (core history)
CREATE TABLE screenings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    input_json JSONB NOT NULL,
    result_json JSONB NOT NULL,
    health_score INT NOT NULL,
    risk_category TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Device connections (Apple Health, Google Fit, CGM)
CREATE TABLE device_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL, -- 'apple_health', 'google_fit', 'dexcom', 'libre'
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Medications (for interaction warnings)
CREATE TABLE medications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    dosage TEXT,
    frequency TEXT,
    started_at DATE,
    ended_at DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Audit logs (compliance)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id UUID,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Third-party API keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL, -- bcrypt hash
    key_prefix TEXT NOT NULL, -- first 8 chars for display
    scopes TEXT[] NOT NULL,
    rate_limit_rpm INT DEFAULT 60,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Row Level Security
ALTER TABLE screenings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own screenings" ON screenings
    USING (user_id = current_setting('app.current_user_id')::UUID);
-- Repeat for all user-scoped tables
```

---

## 4. Enhancements (8 Total)

### 4.1 User Accounts & History Persistence
- **Clerk** handles signup, login, MFA, password reset
- **Neon** stores screening history with full JSON input/output
- **Dashboard**: paginated history, detail view, compare screenings
- **Export**: PDF, CSV, JSON for all screenings

### 4.2 Real-Time Data Integration
- **Apple HealthKit**: HealthKit Entitlements → webhook to `/devices/webhook/apple-health`
- **Google Fit**: OAuth2 + Fitness API → webhook to `/devices/webhook/google-fit`
- **CGM Devices**: Dexcom Share API, LibreView API → polling webhook
- **Background sync**: Vercel Cron (daily) + manual "Sync Now" button
- **Data normalization**: Convert device units → internal mg/dL, mmHg

### 4.3 Offline PWA Mode
- **next-pwa** (Workbox) for service worker
- **IndexedDB** (via `idb` library) for:
  - Pending screenings queue
  - Cached clinical rules (static JSON)
  - Cached ML model (ONNX + onnxruntime-web for true offline inference)
- **Background Sync API**: flush queue when online
- **Offline indicator**: banner + disabled sync buttons

### 4.4 Advanced Risk Modeling
- **SHAP explanations**: `shap.TreeExplainer` for Random Forest → feature importance per prediction
- **Ensemble**: Random Forest + XGBoost + Logistic Regression (soft voting)
- **Uncertainty quantification**: Prediction intervals via quantile regression forests
- **Calibration**: Platt scaling on validation set
- **API**: `/ml/predict` returns `{ probability, shap_values, uncertainty_low, uncertainty_high }`

### 4.5 Third-Party API
- **Authentication**: API keys (scoped: `screening:read`, `screening:write`, `history:read`)
- **Rate limiting**: Redis (Upstash) sliding window per key
- **Webhooks**: User-configurable URLs for `screening.completed`, `emergency.flagged`
- **Documentation**: Auto-generated from OpenAPI at `/api-docs`

### 4.6 FHIR/CDA Export (Added)
- **FHIR R4**: `Observation` resources for glucose, BP, BMI, lipids
- **CDA**: Clinical Document Architecture for EHR import
- **Endpoint**: `GET /screening/{id}/export?format=fhir|cdia`

### 4.7 Automated Model Retraining (Added)
- **Trigger**: Weekly GitHub Action (or on new labeled data)
- **Pipeline**: Pull data → retrain → evaluate → if better, deploy to Vercel
- **Artifacts**: Model versioned in Git LFS or Hugging Face Hub

### 4.8 Feature Flags (Added)
- **Simple JSON config** in Neon: `feature_flags` table
- **Client**: Fetched at app load, cached in Zustand
- **Server**: Middleware checks flags for API routes

---

## 5. Frontend Architecture

### Stack
- **Framework**: Next.js 14.2+ (App Router, React 18, TypeScript strict)
- **Styling**: Tailwind CSS + shadcn/ui (Radix primitives)
- **State**:
  - Server: TanStack Query v5 (caching, deduping, mutations)
  - Client: Zustand (offline queue, UI modals, theme)
- **Forms**: React Hook Form + Zod (schema shared with backend)
- **Charts**: Recharts (health score gauge, trend lines)
- **PDF**: @react-pdf/renderer (client-side PDF generation)
- **Icons**: Lucide React
- **Date**: date-fns

### Key Pages

| Route | Purpose |
|-------|---------|
| `/` | Landing page (marketing, feature highlights) |
| `/sign-in`, `/sign-up` | Clerk-hosted auth pages |
| `/dashboard` | Overview: latest score, quick actions |
| `/dashboard/screening` | 3-step health check (glucose → vitals → review) |
| `/dashboard/history` | Paginated table, filters, compare |
| `/dashboard/history/[id]` | Detail view with SHAP chart |
| `/dashboard/devices` | Connect Apple/Google/CGM, sync status |
| `/dashboard/settings` | Units, theme, notifications, API keys |
| `/api-docs` | Third-party API reference (Scalar/Redoc) |

### Accessibility (WCAG 2.2 AA)
- Semantic HTML, ARIA labels, focus management
- Color contrast ≥ 4.5:1
- Keyboard navigation for all flows
- Screen reader announcements for dynamic results
- Reduced motion support

---

## 6. Deployment & Migration

### CI/CD (GitHub Actions)

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci && npm run lint
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run typecheck
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run test
  build:
    needs: [lint, typecheck, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
```

### Vercel Configuration

```json
// vercel.json
{
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "nextjs",
  "functions": {
    "api/python/**/*.py": {
      "runtime": "python3.11",
      "maxDuration": 30
    }
  },
  "env": {
    "CLERK_PUBLISHABLE_KEY": "@clerk_publishable_key",
    "CLERK_SECRET_KEY": "@clerk_secret_key",
    "DATABASE_URL": "@neon_database_url",
    "UPSTASH_REDIS_REST_URL": "@upstash_redis_url",
    "UPSTASH_REDIS_REST_TOKEN": "@upstash_redis_token"
  }
}
```

### Migration Strategy

1. **Phase 1** (Week 1-2): Scaffold monorepo, port clinical rules + ML to FastAPI, deploy API only
2. **Phase 2** (Week 3-4): Build Next.js frontend screens (screening, history, PDF)
3. **Phase 3** (Week 5): Add auth (Clerk), database (Neon), PWA, device sync
4. **Phase 4** (Week 6): Advanced features (SHAP, ensemble, API, FHIR)
5. **Phase 5** (Week 7): Testing, accessibility audit, performance tuning
6. **Phase 6** (Week 8): Gradual rollout — feature flag `%` traffic to new app, monitor

**Rollback**: Keep Streamlit on `diabetes-prediction-v0.streamlit.app` until 100% parity verified.

---

## 7. Cost Estimate (Student / Free Tier)

| Service | Free Tier Limit | Expected Usage |
|---------|-----------------|----------------|
| Vercel Hobby | 100 GB-hrs/mo | ~10 GB-hrs (10k screenings) |
| Vercel Postgres (Neon) | 0.5 GB storage | ~50 MB (10k screenings) |
| Clerk | 10,000 MAU | < 1,000 MAU |
| Upstash Redis | 10k commands/day | ~1k/day (rate limiting) |
| GitHub Actions | 2,000 min/mo | ~500 min/mo |
| **Total** | **$0/month** | **$0/month** |

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Vercel Python cold starts > 10s | Medium | High | Pre-warm via Vercel Cron; optimize imports; consider Modal fallback |
| Model size > 50MB bundle | Low | High | Current joblib ~8MB; monitor; migrate to Modal if needed |
| Clerk/Neon free tier limits | Low | Medium | Monitor usage; upgrade paths clear ($25/mo each) |
| Apple HealthKit entitlement approval | Medium | Medium | Apply early; fallback to manual CSV import |
| SHAP computation latency | Medium | Medium | Cache explanations; compute async via background job |
| PWA offline complexity | Medium | Medium | Start with service worker caching only; add IndexedDB later |

---

## 9. Success Criteria

- [ ] All current Streamlit features parity in Next.js
- [ ] Screening completes in < 3s (p95) on Vercel
- [ ] PWA works offline for screening + history view
- [ ] Device sync captures ≥ 90% of HealthKit/Fit data
- [ ] Third-party API handles 100 req/min per key
- [ ] WCAG 2.2 AA audit passes
- [ ] Zero-downtime migration from Streamlit
- [ ] Documentation complete (API, user guide, contributing)

---

## 10. Next Steps

1. **Initialize monorepo** with `create-t3-turbo` or manual setup
2. **Port clinical_rules.py** → FastAPI service (pure Python, no Streamlit deps)
3. **Port ml_risk.py** → FastAPI service with joblib loading
4. **Set up Neon + Clerk** locally via docker-compose
5. **Generate OpenAPI** → TypeScript types pipeline
6. **Build screening flow** end-to-end (input → API → result → PDF)
7. **Iterate** through remaining features per phases above