#!/bin/bash

# Script de déploiement rapide AJT Pro
# Usage: ./quick-deploy.sh [branch]

set -e

# Configuration
APP_DIR="/home/ubuntu/ajtpro"
BRANCH="${1:-main}"
DOCKER_COMPOSE_FILE="docker-compose.yml"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')] $1${NC}"
}

echo "⚡ Déploiement rapide AJT Pro - Branche: $BRANCH"
echo "════════════════════════════════════════════════"

# Aller dans le répertoire de l'app
cd "$APP_DIR"

# Vérification rapide
if [ ! -d "frontend" ] || [ ! -d "backend" ]; then
    error "Structure de projet invalide (frontend/ ou backend/ manquant)"
fi

# Mise à jour du code
log "📥 Mise à jour du code..."
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

# Affichage du commit actuel
local commit_hash=$(git rev-parse --short HEAD)
local commit_msg=$(git log -1 --pretty=%B | head -1)
info "Commit: $commit_hash - $commit_msg"

# Build du frontend seulement si nécessaire
if [ -n "$(git diff HEAD~1 --name-only | grep '^frontend/')" ] || [ "$2" = "--force-build" ]; then
    log "🔨 Build du frontend (changements détectés)..."
    cd frontend
    npm ci
    npm run build
    cd ..
else
    info "⏭️  Pas de changements frontend, skip du build"
fi

# Déterminer la commande docker-compose
if command -v "docker compose" &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# Redémarrage intelligent des services
log "🔄 Redémarrage des services..."

# Identifier les services à redémarrer
services_to_restart=""

if [ -n "$(git diff HEAD~1 --name-only | grep '^backend/')" ] || [ "$2" = "--force-restart" ]; then
    services_to_restart="$services_to_restart backend"
    info "🔧 Backend sera redémarré (changements détectés)"
fi

if [ -n "$(git diff HEAD~1 --name-only | grep '^frontend/')" ] || [ "$2" = "--force-restart" ]; then
    services_to_restart="$services_to_restart frontend"
    info "🌐 Frontend sera redémarré (changements détectés)"
fi

# Si aucun changement spécifique, redémarrer tout
if [ -z "$services_to_restart" ]; then
    warn "Aucun changement détecté, redémarrage complet..."
    $DOCKER_COMPOSE_CMD down
    $DOCKER_COMPOSE_CMD up -d --build
else
    # Redémarrage sélectif
    for service in $services_to_restart; do
        log "Redémarrage de $service..."
        $DOCKER_COMPOSE_CMD stop "$service"
        $DOCKER_COMPOSE_CMD build "$service"
        $DOCKER_COMPOSE_CMD up -d "$service"
    done
fi

# Attendre un peu pour le démarrage
log "⏳ Attente du démarrage des services..."
sleep 10

# Tests de santé rapides
log "🏥 Tests de santé..."

# Test frontend
if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
    info "✅ Frontend OK"
else
    warn "⚠️  Frontend non accessible"
fi

# Test backend
if curl -f -s http://localhost:8000 > /dev/null 2>&1; then
    info "✅ Backend OK"
else
    warn "⚠️  Backend non accessible"
fi

# Test base de données
if docker exec postgres pg_isready -U ajt_user -d ajt_db > /dev/null 2>&1; then
    info "✅ Database OK"
else
    warn "⚠️  Database non accessible"
fi

# Affichage du statut final
echo ""
log "📊 Statut des containers:"
$DOCKER_COMPOSE_CMD ps

echo ""
echo "🎉 Déploiement rapide terminé!"
echo "🌍 Frontend: http://$(hostname -I | awk '{print $1}'):3000"
echo "🔧 Backend:  http://$(hostname -I | awk '{print $1}'):8000"

# Affichage des logs récents en cas de problème
if [ "$3" = "--logs" ]; then
    echo ""
    log "📋 Logs récents:"
    $DOCKER_COMPOSE_CMD logs --tail=20
fi