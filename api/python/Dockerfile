# syntax=docker/dockerfile:1
# API-only image.
#
# Use this when the frontend is hosted separately (e.g. Next.js on Vercel) and
# only the FastAPI + ML stack runs in a container. Build from the repository root:
#
#   docker build -f api/python/Dockerfile -t diabetes-prediction-api .
#   docker run -p 8000:8000 --env ENVIRONMENT=development --env DEV_AUTH_BYPASS=true diabetes-prediction-api

FROM python:3.11-slim

# libgomp1 is required by scikit-learn / xgboost at runtime.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Pin BLAS / OpenMP / Numba thread pools. A free-tier instance has a fraction of
# one CPU, and an unbounded pool spawns ~70 threads with per-thread buffers.
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    NUMBA_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1 \
    MALLOC_ARENA_MAX=2

WORKDIR /app

COPY api/python/requirements.txt ./requirements.txt
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r ./requirements.txt \
 && rm ./requirements.txt
ENV PATH="/opt/venv/bin:${PATH}"

# API source, including artifacts/ (model + calibrator + meta bundle).
COPY api/python /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os,urllib.request,sys; port=os.environ.get('PORT','8000'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3).status == 200 else 1)"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
