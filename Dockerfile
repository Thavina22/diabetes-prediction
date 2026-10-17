# syntax=docker/dockerfile:1

########################################
# 1. Build the Next.js frontend
########################################
FROM node:20-bookworm-slim AS web

WORKDIR /build
ENV NEXT_TELEMETRY_DISABLED=1 \
    TURBO_TELEMETRY_DISABLED=1 \
    CI=1

# NEXT_PUBLIC_* values are inlined at build time — pass them as --build-arg when needed.
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=""
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY \
    NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY package.json package-lock.json turbo.json ./
COPY app/package.json app/package.json
COPY packages/shared-types/package.json packages/shared-types/package.json
RUN npm ci

COPY app app
COPY packages packages
RUN npm run build

########################################
# 2. Runtime: Node 20 + Python 3.11
########################################
FROM node:20-bookworm-slim AS runtime

# libgomp1 is required by scikit-learn / xgboost at runtime.
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv libgomp1 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ENV NODE_ENV=production \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=3000 \
    API_INTERNAL_URL=http://127.0.0.1:8000

COPY api/python/requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt
ENV PATH="/opt/venv/bin:${PATH}"

# API source, including api/python/artifacts/ (model + calibrator + meta bundle).
COPY api/python /srv/api

# Next.js standalone server output.
COPY --from=web /build/app/.next/standalone /srv/web
COPY --from=web /build/app/.next/static /srv/web/app/.next/static
COPY --from=web /build/app/public /srv/web/app/public

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /srv/web
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

CMD ["/usr/local/bin/entrypoint.sh"]
