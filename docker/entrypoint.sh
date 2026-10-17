#!/bin/bash
set -euo pipefail

export HOSTNAME="${HOSTNAME:-0.0.0.0}"
export PORT="${PORT:-3000}"
export API_INTERNAL_URL="${API_INTERNAL_URL:-http://127.0.0.1:8000}"

echo "[entrypoint] starting FastAPI on 127.0.0.1:8000"
uvicorn main:app --host 127.0.0.1 --port 8000 --app-dir /srv/api &
API_PID=$!

echo "[entrypoint] waiting for the API to become healthy..."
for _ in $(seq 1 60); do
  if python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)" 2>/dev/null; then
    echo "[entrypoint] API is ready"
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "[entrypoint] API process exited during startup" >&2
    exit 1
  fi
  sleep 1
done

echo "[entrypoint] starting Next.js on ${HOSTNAME}:${PORT}"
node /srv/web/app/server.js &
WEB_PID=$!

shutdown() {
  echo "[entrypoint] shutting down"
  kill -TERM "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap shutdown TERM INT

# Exit the container when either process exits so the platform can restart it.
wait -n "$API_PID" "$WEB_PID"
STATUS=$?
shutdown
wait 2>/dev/null || true
exit "$STATUS"
