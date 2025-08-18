#!/bin/bash

# Script de déploiement d'urgence AJT Pro
# Usage: ./emergency-deploy.sh
# Ce script contourne les problèmes Git et de sauvegarde

set -e

# Configuration
APP_DIR="/home/ubuntu/ajtpro"
DOCKER_COMPOSE_FILE="docker-compose.yml"
DOCKER_COMPOSE_PROD_FILE="docker-compose.prod.yml"

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
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')] INFO: $1${NC}"
}

echo "🚨 DÉPLOIEMENT D'URGENCE AJT PRO"
echo "═══════════════════════════════════════════════"
warn "⚠️  Ce script contourne les vérifications Git et de sauvegarde"
warn "⚠️  Utilisez uniquement en cas d'urgence"
echo ""

read -p "Continuer avec le déploiement d'urgence? (oui/non): " confirm
if [ "$confirm" != "oui" ]; then
    log "Déploiement annulé"
    exit 0
fi

# Aller dans le répertoire de l'application
cd "$APP_DIR" || error "Impossible d'accéder à $APP_DIR"

# Vérification de la structure minimale
log "🔍 Vérification de la structure..."

required_items=("frontend" "backend" "docker-compose.yml")
missing_items=()

for item in "${required_items[@]}"; do
    if [ ! -e "$item" ]; then
        missing_items+=("$item")
    fi
done

if [ ${#missing_items[@]} -gt 0 ]; then
    error "❌ Éléments manquants: ${missing_items[*]}"
fi

info "✅ Structure de base présente"

# Build du frontend (si possible)
log "🏗️ Tentative de build du frontend..."

if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    cd frontend
    
    log "📦 Installation des dépendances..."
    if npm ci --production=false 2>/dev/null; then
        info "✅ Dépendances installées"
        
        log "🔨 Build du frontend..."
        if npm run build 2>/dev/null; then
            info "✅ Frontend buildé avec succès"
        else
            warn "⚠️  Échec du build frontend, continue quand même..."
        fi
    else
        warn "⚠️  Échec de l'installation des dépendances, continue quand même..."
    fi
    
    cd "$APP_DIR"
else
    warn "⚠️  Frontend non buildable, continue quand même..."
fi

# Choix du fichier docker-compose
compose_file="$DOCKER_COMPOSE_FILE"
if [ -f "$DOCKER_COMPOSE_PROD_FILE" ]; then
    echo ""
    echo "Fichiers docker-compose disponibles:"
    echo "1. $DOCKER_COMPOSE_FILE (développement)"
    echo "2. $DOCKER_COMPOSE_PROD_FILE (production)"
    echo ""
    read -p "Choisir le fichier (1/2): " choice
    
    if [ "$choice" = "2" ]; then
        compose_file="$DOCKER_COMPOSE_PROD_FILE"
        info "Utilisation du fichier de production: $compose_file"
    fi
fi

# Déterminer la commande docker-compose
if command -v "docker compose" &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# Vérification du réseau Docker
log "🌐 Vérification du réseau Docker..."
if ! docker network ls | grep -q "ajtpro_default"; then
    log "Création du réseau ajtpro_default..."
    docker network create ajtpro_default || warn "Échec de création du réseau (peut déjà exister)"
fi

# Arrêt des services existants
log "⏹️ Arrêt des services existants..."
$DOCKER_COMPOSE_CMD -f "$compose_file" down --remove-orphans 2>/dev/null || warn "Erreur lors de l'arrêt (non critique)"

# Nettoyage optionnel
read -p "🧹 Nettoyer les images Docker inutilisées? (y/N): " clean_images
if [[ $clean_images =~ ^[Yy]$ ]]; then
    log "Nettoyage des images..."
    docker system prune -f || warn "Erreur lors du nettoyage (non critique)"
fi

# Reconstruction et démarrage
log "🔨 Reconstruction des images..."
$DOCKER_COMPOSE_CMD -f "$compose_file" build --no-cache || error "Échec de la reconstruction"

log "🚀 Démarrage des services..."
$DOCKER_COMPOSE_CMD -f "$compose_file" up -d || error "Échec du démarrage"

# Attente du démarrage
log "⏳ Attente du démarrage des services..."
sleep 15

# Vérification du statut
log "📊 Statut des services:"
$DOCKER_COMPOSE_CMD -f "$compose_file" ps

# Tests de connectivité simples
echo ""
log "🏥 Tests de connectivité..."

# Test frontend
if curl -f -s http://localhost:3000 >/dev/null 2>&1; then
    info "✅ Frontend accessible (port 3000)"
else
    warn "⚠️ Frontend non accessible (port 3000)"
fi

# Test backend
if curl -f -s http://localhost:8000 >/dev/null 2>&1; then
    info "✅ Backend accessible (port 8000)"
else
    warn "⚠️ Backend non accessible (port 8000)"
fi

# Test PostgreSQL
if docker exec postgres pg_isready -U ajt_user -d ajt_db >/dev/null 2>&1; then
    info "✅ PostgreSQL accessible"
else
    warn "⚠️ PostgreSQL non accessible"
fi

# Informations finales
echo ""
echo "═══════════════════════════════════════════════"
log "📋 INFORMATIONS DE DÉPLOIEMENT"

local_ip=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

echo ""
echo "🌍 URLs d'accès:"
echo "  Frontend: http://$local_ip:3000"
echo "  Backend:  http://$local_ip:8000"
echo ""
echo "🔧 Commandes utiles:"
echo "  Logs:     $DOCKER_COMPOSE_CMD -f $compose_file logs -f"
echo "  Statut:   $DOCKER_COMPOSE_CMD -f $compose_file ps"
echo "  Arrêt:    $DOCKER_COMPOSE_CMD -f $compose_file down"
echo ""
echo "📁 Répertoire: $APP_DIR"
echo "📄 Config:     $compose_file"

# Vérification finale
all_ok=true

echo ""
echo "🔍 Vérification finale:"

# Vérifier que les containers sont en cours d'exécution
expected_containers=("ajt_frontend" "ajt_backend" "postgres")
for container in "${expected_containers[@]}"; do
    if docker ps --format "{{.Names}}" | grep -q "^$container$"; then
        echo "  ✅ $container en cours d'exécution"
    else
        echo "  ❌ $container non trouvé"
        all_ok=false
    fi
done

echo ""
if [ "$all_ok" = true ]; then
    log "🎉 Déploiement d'urgence terminé avec succès!"
    info "⚠️  N'oubliez pas de corriger les problèmes Git et de sauvegarde plus tard"
    
    echo ""
    echo "🔄 Pour corriger les problèmes identifiés:"
    echo "1. ./diagnostic.sh           # Analyser les problèmes"
    echo "2. ./fix-git.sh             # Corriger Git"
    echo "3. ./fix-backup.sh          # Corriger les sauvegardes"
    echo "4. ./deploy.sh install_prod # Déploiement normal"
else
    warn "⚠️ Déploiement partiellement réussi - Vérifiez les logs"
    echo ""
    echo "🔍 Pour diagnostiquer:"
    echo "  $DOCKER_COMPOSE_CMD -f $compose_file logs"
fi

echo ""
echo "⏰ Durée totale: $SECONDS secondes"