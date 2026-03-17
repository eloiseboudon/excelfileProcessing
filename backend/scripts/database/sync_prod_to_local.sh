#!/bin/bash
# sync_prod_to_local.sh — Télécharge un dump de la base prod et le restaure en local
#
# Usage: bash backend/scripts/database/sync_prod_to_local.sh
#
# Prérequis:
#   - Accès SSH au VPS (ubuntu@51.77.231.101)
#   - Container postgres_dev en cours d'exécution localement
#   - Fichier .env à la racine du projet avec POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DUMP_DIR="$PROJECT_ROOT/tmp"
DUMP_FILE="$DUMP_DIR/prod_dump.sql"

VPS_HOST="ubuntu@51.77.231.101"
LOCAL_CONTAINER="postgres_dev"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[sync] $1${NC}"; }
warn() { echo -e "${YELLOW}[sync] WARN: $1${NC}"; }
fail() { echo -e "${RED}[sync] FATAL: $1${NC}"; exit 1; }

# Load local .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    fail ".env introuvable dans $PROJECT_ROOT"
fi

LOCAL_DB="${POSTGRES_DB:?POSTGRES_DB manquant dans .env}"
LOCAL_USER="${POSTGRES_USER:?POSTGRES_USER manquant dans .env}"
LOCAL_PASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD manquant dans .env}"

# Check local container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${LOCAL_CONTAINER}$"; then
    fail "Container $LOCAL_CONTAINER non démarré. Lancez: docker compose up -d postgres"
fi

mkdir -p "$DUMP_DIR"

# 1. Dump prod via SSH
log "Dump de la base prod sur le VPS..."
ssh "$VPS_HOST" 'cd ~/ajtpro && \
    PG_USER=$(grep -m1 "^POSTGRES_USER=" .env | cut -d= -f2) && \
    PG_DB=$(grep -m1 "^POSTGRES_DB=" .env | cut -d= -f2) && \
    docker exec postgres_prod pg_dump -U "$PG_USER" -d "$PG_DB" --no-owner --no-acl' > "$DUMP_FILE"

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
log "Dump téléchargé: $DUMP_SIZE"

# 2. Drop & recreate local DB
log "Réinitialisation de la base locale..."
docker exec -e PGPASSWORD="$LOCAL_PASSWORD" "$LOCAL_CONTAINER" \
    psql -U "$LOCAL_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$LOCAL_DB' AND pid <> pg_backend_pid();"
docker exec -e PGPASSWORD="$LOCAL_PASSWORD" "$LOCAL_CONTAINER" \
    psql -U "$LOCAL_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$LOCAL_DB\";"
docker exec -e PGPASSWORD="$LOCAL_PASSWORD" "$LOCAL_CONTAINER" \
    psql -U "$LOCAL_USER" -d postgres -c "CREATE DATABASE \"$LOCAL_DB\" OWNER \"$LOCAL_USER\";"

# 3. Restore dump into local DB
log "Restauration du dump en local..."
docker exec -i -e PGPASSWORD="$LOCAL_PASSWORD" "$LOCAL_CONTAINER" \
    psql -U "$LOCAL_USER" -d "$LOCAL_DB" < "$DUMP_FILE"

# 4. Cleanup
rm -f "$DUMP_FILE"
log "Dump temporaire supprimé"

# 5. Verify
TABLE_COUNT=$(docker exec -e PGPASSWORD="$LOCAL_PASSWORD" "$LOCAL_CONTAINER" \
    psql -U "$LOCAL_USER" -d "$LOCAL_DB" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
PRODUCT_COUNT=$(docker exec -e PGPASSWORD="$LOCAL_PASSWORD" "$LOCAL_CONTAINER" \
    psql -U "$LOCAL_USER" -d "$LOCAL_DB" -t -c "SELECT count(*) FROM products;" 2>/dev/null || echo "0")

log "===== SYNC TERMINÉ ====="
log "Tables: $(echo $TABLE_COUNT | xargs)"
log "Produits: $(echo $PRODUCT_COUNT | xargs)"
