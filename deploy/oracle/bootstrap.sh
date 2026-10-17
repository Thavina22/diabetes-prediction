#!/usr/bin/env bash
# One-shot bootstrap for the single-container deployment (Oracle Cloud Always Free,
# or any Ubuntu VM). Idempotent: re-run it to pull the latest code and rebuild.
#
#   curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/deploy/oracle/bootstrap.sh | bash
#
# Override any of the values below with environment variables, e.g.
#   ENVIRONMENT=production DEV_AUTH_BYPASS=false bash bootstrap.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/sam-black007/diabetes-prediction.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-/opt/diabetes-prediction}"
APP_PORT="${APP_PORT:-3000}"
IMAGE="${IMAGE:-diabetes-prediction:latest}"
CONTAINER="${CONTAINER:-diabetes-prediction}"

ENVIRONMENT="${ENVIRONMENT:-development}"
DEV_AUTH_BYPASS="${DEV_AUTH_BYPASS:-true}"

log() { printf '\n=== %s ===\n' "$*"; }

log "Installing Docker and git"
if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl git
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
fi
sudo systemctl enable --now docker

# Oracle's Ubuntu images ship with a restrictive iptables ruleset that drops
# traffic before it ever reaches the VCN security list. Open the app port here too.
log "Opening port ${APP_PORT} in the host firewall"
sudo iptables -C INPUT -p tcp --dport "${APP_PORT}" -j ACCEPT 2>/dev/null \
  || sudo iptables -I INPUT -p tcp --dport "${APP_PORT}" -j ACCEPT
if command -v netfilter-persistent >/dev/null 2>&1; then
  sudo netfilter-persistent save || true
else
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent >/dev/null 2>&1 || true
  sudo netfilter-persistent save 2>/dev/null || true
fi

log "Fetching the code"
sudo mkdir -p "$APP_DIR" && sudo chown "$USER" "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch --all --prune
  git -C "$APP_DIR" reset --hard "origin/${BRANCH}"
else
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

log "Building the image (first build takes several minutes)"
sudo docker build -t "$IMAGE" "$APP_DIR"

log "Starting the container"
sudo docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
ENV_FILE_ARGS=()
if [ -f "$APP_DIR/.env.production" ]; then
  ENV_FILE_ARGS=(--env-file "$APP_DIR/.env.production")
fi
sudo docker run -d --name "$CONTAINER" --restart unless-stopped \
  -p "${APP_PORT}:3000" \
  -e ENVIRONMENT="${ENVIRONMENT}" \
  -e DEV_AUTH_BYPASS="${DEV_AUTH_BYPASS}" \
  "${ENV_FILE_ARGS[@]}" \
  "$IMAGE"

log "Cleaning up old images"
sudo docker image prune -f >/dev/null 2>&1 || true

PUBLIC_IP="$(curl -fsS --max-time 5 https://ifconfig.me 2>/dev/null || true)"
log "Done"
echo "App:     http://${PUBLIC_IP:-<vm-public-ip>}:${APP_PORT}"
echo "Health:  http://${PUBLIC_IP:-<vm-public-ip>}:${APP_PORT}/api/v1/features"
echo "Logs:    sudo docker logs -f ${CONTAINER}"
