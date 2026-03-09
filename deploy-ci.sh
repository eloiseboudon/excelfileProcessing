#!/bin/bash
# deploy-ci.sh - Script de deploiement non-interactif pour CI/CD
# Appele par GitHub Actions via SSH apres push sur main

set -euo pipefail

APP_DIR="/home/ubuntu/ajtpro"
COMPOSE_FILE="docker-compose.prod.yml"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN: $1${NC}"; }
fail() { echo -e "${RED}[$(date '+%H:%M:%S')] FATAL: $1${NC}"; exit 1; }

cd "$APP_DIR" || fail "Repertoire $APP_DIR introuvable"

# Load environment variables from .env
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
else
    warn ".env file not found, using environment defaults"
fi

# 1. Backup DB
log "Backup de la base de donnees..."
if [ -f "./save_db.sh" ]; then
    chmod +x ./save_db.sh
    ./save_db.sh "before_deploy_ci_$(date +%Y%m%d_%H%M%S)" || warn "Backup DB echoue (non critique)"
else
    warn "save_db.sh absent, pas de backup DB"
fi

# 2. Pull du code
log "Pull du code depuis origin/main..."
git fetch origin
git reset --hard origin/main

# 3. Inject catalogue upload token into admin.html and systemd service
if [ -n "${CATALOGUE_UPLOAD_TOKEN:-}" ]; then
    sed -i 's/data-upload-token="REPLACE_IN_PROD"/data-upload-token="'"$CATALOGUE_UPLOAD_TOKEN"'"/' \
      "$APP_DIR/catalogue/admin.html"
    log "Catalogue upload token injecte dans admin.html"

    # Update systemd service with the real token
    SERVICE_FILE="/etc/systemd/system/catalogue-upload.service"
    if [ -f "$SERVICE_FILE" ]; then
        sudo sed -i 's|Environment=UPLOAD_TOKEN=.*|Environment=UPLOAD_TOKEN='"$CATALOGUE_UPLOAD_TOKEN"'|' "$SERVICE_FILE"
        sudo systemctl daemon-reload
        log "Catalogue upload token injecte dans systemd service"
    fi
fi

# 3b. Restart catalogue upload server if running
if systemctl is-active --quiet catalogue-upload 2>/dev/null; then
    sudo systemctl restart catalogue-upload || warn "Restart catalogue-upload echoue"
    log "catalogue-upload redémarre"
fi

# 4. Verification des fichiers .env
log "Verification des fichiers .env..."
for envfile in .env backend/.env frontend/.env; do
    if [ -f "$envfile" ]; then
        log "  $envfile present"
    fi
done

# 5. Injection des secrets dans .env
for SECRET_NAME in ODOO_ENCRYPTION_KEY ANTHROPIC_API_KEY; do
    SECRET_VALUE=$(eval echo "\${${SECRET_NAME}:-}")
    if [ -n "$SECRET_VALUE" ]; then
        if grep -q "^${SECRET_NAME}=" "$APP_DIR/.env" 2>/dev/null; then
            sed -i "s|^${SECRET_NAME}=.*|${SECRET_NAME}=${SECRET_VALUE}|" "$APP_DIR/.env"
            log "${SECRET_NAME} mise a jour dans .env"
        else
            echo "${SECRET_NAME}=${SECRET_VALUE}" >> "$APP_DIR/.env"
            log "${SECRET_NAME} ajoutee dans .env"
        fi
    fi
done

# 6. Build et (re)demarrage des containers
log "Build et demarrage des containers..."
docker compose -f "$COMPOSE_FILE" up --build -d --remove-orphans

# 7. Fix alembic stamp if legacy revision name exists (one-time fix)
PG_USER="$(grep -m1 '^POSTGRES_USER=' "$APP_DIR/.env" | cut -d= -f2)"
PG_DB="$(grep -m1 '^POSTGRES_DB=' "$APP_DIR/.env" | cut -d= -f2)"
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U "${PG_USER}" -d "${PG_DB}" -c \
  "UPDATE alembic_version SET version_num = 'v2_populate_ram' WHERE version_num = 'v2_populate_ram_from_description';" 2>/dev/null \
  && log "Alembic stamp corrige (legacy rename)" || true

# 8. Attente DB + migrations Alembic
log "Attente que la base de donnees demarre..."
for i in $(seq 1 30); do
    if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "${PG_USER}" 2>/dev/null; then
        log "Base de donnees prete"
        break
    fi
    if [ "$i" -eq 30 ]; then
        fail "DB non prete apres 60s"
    fi
    sleep 2
done

# Run migrations once
log "Application des migrations Alembic..."
docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head || warn "Migrations echouees"

# 9. Health checks
log "Health checks..."
HEALTH_OK=true

for i in $(seq 1 30); do
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        log "Frontend OK (port 3000)"
        break
    fi
    if [ "$i" -eq 30 ]; then
        warn "Frontend non accessible apres 30 tentatives"
        HEALTH_OK=false
    fi
    sleep 2
done

for i in $(seq 1 30); do
    if curl -sf http://localhost:8000 > /dev/null 2>&1; then
        log "Backend OK (port 8000)"
        break
    fi
    if [ "$i" -eq 30 ]; then
        warn "Backend non accessible apres 30 tentatives"
        HEALTH_OK=false
    fi
    sleep 2
done

# 10. Nettoyage images Docker
docker image prune -f > /dev/null 2>&1 || true

# 11. Resume
echo ""
log "===== DEPLOIEMENT TERMINE ====="
log "Commit  : $(git rev-parse --short HEAD)"
log "Auteur  : $(git log -1 --format='%an')"
log "Date    : $(git log -1 --format='%cd' --date=short)"
log "Message : $(git log -1 --format='%s')"
if [ "$HEALTH_OK" = true ]; then
    log "Statut  : OK"
else
    warn "Statut  : DEGRADED (verifier les health checks)"
fi
docker compose -f "$COMPOSE_FILE" ps
