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

# 3. Sauvegarde et restauration des .env
log "Verification des fichiers .env..."
for envfile in .env backend/.env frontend/.env; do
    if [ -f "$envfile" ]; then
        log "  $envfile present"
    fi
done

# 4. Injection des secrets dans .env
if [ -n "${ODOO_ENCRYPTION_KEY:-}" ]; then
    if grep -q "^ODOO_ENCRYPTION_KEY=" "$APP_DIR/.env" 2>/dev/null; then
        sed -i "s|^ODOO_ENCRYPTION_KEY=.*|ODOO_ENCRYPTION_KEY=${ODOO_ENCRYPTION_KEY}|" "$APP_DIR/.env"
        log "ODOO_ENCRYPTION_KEY mise a jour dans .env"
    else
        echo "ODOO_ENCRYPTION_KEY=${ODOO_ENCRYPTION_KEY}" >> "$APP_DIR/.env"
        log "ODOO_ENCRYPTION_KEY ajoutee dans .env"
    fi
fi

# 5. Build frontend
log "Build du frontend..."
cd "$APP_DIR/frontend"
npm ci
npm run build
cd "$APP_DIR"

# 6. Arret des containers
log "Arret des containers..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans || warn "Erreur lors de l'arret (non critique)"

# Nettoyage des conteneurs nommes et du reseau si le down n'a pas suffi
log "Nettoyage des conteneurs residuels..."
docker rm -f postgres_prod ajt_backend_prod ajt_frontend_prod 2>/dev/null || true
docker network rm ajtpro_default 2>/dev/null || true

# 7. Rebuild des images
log "Rebuild des images Docker..."
docker compose -f "$COMPOSE_FILE" build --no-cache

# 8. Demarrage des containers
log "Demarrage des containers..."
docker compose -f "$COMPOSE_FILE" up -d

# 9. Attente + migrations Alembic
log "Attente que les services demarrent (30s)..."
sleep 30

log "Application des migrations Alembic..."
docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head || warn "Migrations echouees ou non necessaires"

# 10. Health checks
log "Health checks..."
HEALTH_OK=true

for i in $(seq 1 10); do
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        log "Frontend OK (port 3000)"
        break
    fi
    if [ "$i" -eq 10 ]; then
        warn "Frontend non accessible apres 10 tentatives"
        HEALTH_OK=false
    fi
    sleep 5
done

for i in $(seq 1 10); do
    if curl -sf http://localhost:8000 > /dev/null 2>&1; then
        log "Backend OK (port 8000)"
        break
    fi
    if [ "$i" -eq 10 ]; then
        warn "Backend non accessible apres 10 tentatives"
        HEALTH_OK=false
    fi
    sleep 5
done

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
