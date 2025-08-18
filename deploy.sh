#!/bin/bash

# Script de déploiement automatisé
# Usage: ./deploy.sh [branch_name]

set -e  # Arrêt du script en cas d'erreur

# Configuration
REPO_URL="https://github.com/votre-username/votre-repo.git"  # À adapter
APP_DIR="/opt/votre-app"  # Répertoire de l'application
BRANCH="${1:-install_prod}"  # Branche par défaut ou celle passée en paramètre
DOCKER_COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="/opt/backups/$(date +%Y%m%d_%H%M%S)"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    if ! command -v git &> /dev/null; then
        error "Git n'est pas installé"
    fi
    
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
        error "Docker Compose n'est pas installé"
    fi
    
    if ! command -v npm &> /dev/null; then
        error "NPM n'est pas installé"
    fi
}

# Sauvegarde de l'application actuelle
backup_current_version() {
    if [ -d "$APP_DIR" ]; then
        log "Sauvegarde de la version actuelle vers $BACKUP_DIR..."
        mkdir -p "$BACKUP_DIR"
        cp -r "$APP_DIR" "$BACKUP_DIR/"
    fi
}

# Récupération du code depuis Git
fetch_code() {
    log "Récupération du code depuis Git (branche: $BRANCH)..."
    
    if [ ! -d "$APP_DIR" ]; then
        log "Clone du repository..."
        git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
    else
        log "Mise à jour du code existant..."
        cd "$APP_DIR"
        
        # Sauvegarde des changements locaux potentiels
        if ! git diff --quiet; then
            warn "Des changements locaux détectés, création d'un stash..."
            git stash
        fi
        
        git fetch origin
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
    fi
    
    cd "$APP_DIR"
}

# Build du frontend
build_frontend() {
    log "Installation des dépendances NPM..."
    npm ci --production=false
    
    log "Build du frontend..."
    npm run build
    
    # Vérification que le build a réussi
    if [ ! -d "dist" ] && [ ! -d "build" ]; then
        error "Le répertoire de build (dist/build) n'existe pas après le build"
    fi
}

# Gestion des containers Docker
manage_docker_containers() {
    log "Arrêt des containers Docker..."
    
    # Utilisation de docker compose ou docker-compose selon la version
    if command -v "docker compose" &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        DOCKER_COMPOSE_CMD="docker-compose"
    fi
    
    # Arrêt propre des containers
    if [ -f "$DOCKER_COMPOSE_FILE" ]; then
        $DOCKER_COMPOSE_CMD down --remove-orphans
    else
        warn "Fichier docker-compose.yml introuvable, arrêt manuel des containers..."
        docker stop $(docker ps -q) 2>/dev/null || true
    fi
    
    log "Reconstruction et démarrage des containers..."
    
    # Reconstruction des images si nécessaire
    $DOCKER_COMPOSE_CMD build --no-cache
    
    # Démarrage des containers
    $DOCKER_COMPOSE_CMD up -d
    
    # Attendre que les services soient prêts
    log "Attente du démarrage des services..."
    sleep 10
}

# Vérification de la santé de l'application
health_check() {
    log "Vérification de la santé de l'application..."
    
    # À adapter selon votre configuration
    LOCAL_URL="http://localhost:3000"  # Port de votre application
    
    for i in {1..10}; do
        if curl -f -s "$LOCAL_URL" > /dev/null; then
            log "Application accessible et fonctionnelle !"
            return 0
        fi
        warn "Tentative $i/10 - En attente de la disponibilité de l'application..."
        sleep 5
    done
    
    error "L'application ne répond pas après le déploiement"
}

# Rollback en cas d'échec
rollback() {
    error "Échec du déploiement, rollback en cours..."
    
    if [ -d "$BACKUP_DIR" ]; then
        log "Restauration de la version précédente..."
        rm -rf "$APP_DIR"
        cp -r "$BACKUP_DIR/$(basename $APP_DIR)" "$APP_DIR"
        cd "$APP_DIR"
        manage_docker_containers
    fi
}

# Nettoyage des anciennes sauvegardes (garde les 5 dernières)
cleanup_old_backups() {
    log "Nettoyage des anciennes sauvegardes..."
    find "/opt/backups" -maxdepth 1 -type d -name "20*" | sort -r | tail -n +6 | xargs rm -rf 2>/dev/null || true
}

# Fonction principale
main() {
    log "Début du déploiement automatisé..."
    
    # Trap pour gérer les erreurs
    trap rollback ERR
    
    check_prerequisites
    backup_current_version
    fetch_code
    build_frontend
    manage_docker_containers
    health_check
    cleanup_old_backups
    
    log "Déploiement terminé avec succès !"
    log "Application accessible via votre adresse IP"
}

# Exécution du script
main "$@"