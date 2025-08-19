#!/bin/bash

# Script de déploiement automatisé AJT Pro
# Usage: ./deploy.sh [branch_name]

set -e  # Arrêt du script en cas d'erreur

# Configuration
REPO_URL="https://github.com/votre-username/ajtpro.git"  # À adapter
APP_DIR="/home/ubuntu/ajtpro"  # Répertoire actuel de l'application
BRANCH="${1:-main}"  # Branche par défaut ou celle passée en paramètre
DOCKER_COMPOSE_FILE="docker-compose.yml"
DOCKER_COMPOSE_PROD_FILE="docker-compose.prod.yml"
BACKUP_DIR="/home/ubuntu/backups_ajtpro/deployments/$(date +%Y%m%d_%H%M%S)"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Vérification des prérequis
check_prerequisites() {
    log "🔍 Vérification des prérequis..."
    
    if ! command -v git &> /dev/null; then
        error "Git n'est pas installé"
    fi
    
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
        error "Docker Compose n'est pas installé"
    fi
    
    info "✅ Tous les prérequis sont satisfaits"
}

# Création/vérification du réseau Docker
setup_docker_network() {
    log "🌐 Configuration du réseau Docker..."
    
    # Vérifier si le réseau existe déjà  
    if docker network ls --format "table {{.Name}}" | grep -q "^ajtpro_default$"; then
        info "✅ Le réseau ajtpro_default existe déjà"
    else
        log "📡 Création du réseau Docker ajtpro_default..."
        docker network create ajtpro_default
        info "✅ Réseau ajtpro_default créé avec succès"
    fi
}

# Sauvegarde de la base de données avant déploiement
backup_database() {
    log "💾 Sauvegarde de la base de données avant déploiement..."
    
    if [ -f "./save_db.sh" ]; then
        # S'assurer que le script est exécutable
        chmod +x ./save_db.sh
        ./save_db.sh "before_deploy_$(date +%Y%m%d_%H%M%S)" || warn "Échec de la sauvegarde DB (non critique)"
    else
        warn "Script save_db.sh introuvable, pas de sauvegarde DB"
    fi
}

# Sauvegarde de l'application actuelle
backup_current_version() {
    log "📦 Sauvegarde de la version actuelle..."
    
    if [ -d "$APP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        # Sauvegarde uniquement les fichiers essentiels (pas node_modules, dist, etc.)
        tar --exclude='*/node_modules' \
            --exclude='*/dist' \
            --exclude='*/build' \
            --exclude='*/.git' \
            --exclude='*/coverage' \
            -czf "$BACKUP_DIR/app_backup.tar.gz" \
            -C "$(dirname "$APP_DIR")" "$(basename "$APP_DIR")"
        
        info "Sauvegarde créée : $BACKUP_DIR/app_backup.tar.gz"
    fi
}

# Récupération du code depuis Git
fetch_code() {
    log "📥 Récupération du code depuis Git (branche: $BRANCH)..."
    
    cd "$APP_DIR"
    
    # Vérification du statut Git
    if ! git status &>/dev/null; then
        error "Le répertoire n'est pas un repository Git valide"
    fi
    
    # Sauvegarde des changements locaux potentiels
    if ! git diff --quiet; then
        warn "Des changements locaux détectés, création d'un stash..."
        git stash push -m "Auto-stash before deploy $(date)"
    fi
    
    # Mise à jour du code
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
    
    local commit_hash=$(git rev-parse --short HEAD)
    local commit_msg=$(git log -1 --pretty=%B | head -1)
    
    info "✅ Code mis à jour - Commit: $commit_hash"
    info "📝 Message: $commit_msg"
}

# Build du frontend avec gestion des erreurs et récupération
build_frontend() {
    log "🗃️ Build du frontend..."
    
    cd "$APP_DIR/frontend"
    
    # Vérification de package.json
    if [ ! -f "package.json" ]; then
        error "package.json introuvable dans le répertoire frontend"
    fi
    
    # Installation des dépendances avec gestion d'erreur
    log "📦 Installation des dépendances NPM..."
    if ! npm ci --production=false; then
        warn "⚠️ npm ci a échoué, tentative de correction..."
        
        # Correction du problème Rollup/npm
        log "🔧 Correction du problème de dépendances..."
        rm -rf node_modules package-lock.json
        npm cache clean --force
        
        if npm install --legacy-peer-deps; then
            info "✅ Dépendances installées avec --legacy-peer-deps"
        elif npm install --force; then
            info "✅ Dépendances installées avec --force"
        else
            error "❌ Impossible d'installer les dépendances"
        fi
    fi
    
    # Build de production avec récupération
    log "🔨 Build de production..."
    if ! npm run build; then
        warn "⚠️ Premier build échoué, tentative de correction..."
        
        # Réinstaller Rollup spécifiquement
        npm install rollup@latest --save-dev --legacy-peer-deps || true
        
        # Retry le build
        if npm run build; then
            info "✅ Build réussi après correction"
        else
            error "❌ Build définitivement échoué"
        fi
    fi
    
    # Vérification que le build a réussi
    if [ ! -d "dist" ] && [ ! -d "build" ]; then
        error "Le répertoire de build (dist/build) n'existe pas après le build"
    fi
    
    local build_size=$(du -sh dist 2>/dev/null || du -sh build 2>/dev/null || echo "N/A")
    info "✅ Frontend buildé avec succès - Taille: $build_size"
    
    cd "$APP_DIR"
}

# Gestion des containers Docker avec validation
manage_docker_containers() {
    log "🐳 Gestion des containers Docker..."
    
    cd "$APP_DIR"
    
    # Déterminer la commande docker-compose
    DOCKER_COMPOSE_CMD="docker compose"

    # Choisir le bon fichier docker-compose
    local compose_file="$DOCKER_COMPOSE_FILE"
    if [ -f "$DOCKER_COMPOSE_PROD_FILE" ]; then
        read -p "Utiliser le fichier de production ? (y/N): " use_prod
        if [[ $use_prod =~ ^[Yy]$ ]]; then
            compose_file="$DOCKER_COMPOSE_PROD_FILE"
            info "Utilisation du fichier de production: $compose_file"
        fi
    fi
    
    # Arrêt propre des containers existants
    log "⏹️ Arrêt des containers..."
    $DOCKER_COMPOSE_CMD -f "$compose_file" down --remove-orphans || warn "Erreur lors de l'arrêt (non critique)"
    
    # Nettoyage des images non utilisées (optionnel)
    log "🧹 Nettoyage des images Docker..."
    docker system prune -f --volumes || warn "Erreur lors du nettoyage (non critique)"
    
    # Reconstruction des images
    log "🔄 Reconstruction des images..."
    $DOCKER_COMPOSE_CMD -f "$compose_file" build --no-cache
    
    # Démarrage des containers
    log "🚀 Démarrage des containers..."
    $DOCKER_COMPOSE_CMD -f "$compose_file" up -d
    
    # Attendre que les services soient prêts
    log "⏳ Attente que les services soient prêts..."
    sleep 10
    
    # Stockage de la commande docker-compose pour les migrations
    export DOCKER_COMPOSE_CMD="$DOCKER_COMPOSE_CMD"
    export COMPOSE_FILE="$compose_file"
    
    # Affichage du statut
    log "📊 Statut des containers:"
    $DOCKER_COMPOSE_CMD -f "$compose_file" ps
}

# Gestion des migrations Alembic - VERSION AMÉLIORÉE
run_database_migrations() {
    log "🗃️ Gestion des migrations de base de données avec Alembic..."
    
    cd "$APP_DIR"
    
    # Vérification que les containers sont en cours d'exécution
    if ! $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps backend | grep -q "Up"; then
        error "Le container backend n'est pas en cours d'exécution"
    fi
    
    # Attendre que la base de données soit prête avec plusieurs méthodes
    log "⏳ Attente que la base de données soit prête..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # Test avec pg_isready depuis le container postgres
        if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
            info "✅ Base de données PostgreSQL prête"
            break
        fi
        
        # Test de connexion simple avec psql
        if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres psql -h localhost -U "${POSTGRES_USER:-ajt_user}" -d "${POSTGRES_DB:-ajt_db}" -c "SELECT 1;" >/dev/null 2>&1; then
            info "✅ Base de données accessible"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            # Diagnostic en cas d'échec
            warn "🔍 Diagnostic de la base de données..."
            
            log "📊 Statut des containers:"
            $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps
            
            log "📋 Logs PostgreSQL (dernières 10 lignes):"
            $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" logs --tail=10 postgres || true
            
            log "📋 Logs Backend (dernières 10 lignes):"
            $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" logs --tail=10 backend || true
            
            error "❌ Timeout: la base de données n'est pas accessible après $max_attempts tentatives"
        fi
        
        warn "Tentative $attempt/$max_attempts - Base de données pas encore prête..."
        sleep 5
        ((attempt++))
    done
    
    # 1. Vérifier l'état actuel des migrations AVANT de faire quoi que ce soit
    log "📋 Vérification de l'état actuel des migrations..."
    local current_migration=""
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic current >/dev/null 2>&1; then
        current_migration=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic current 2>/dev/null | grep -E "^[a-f0-9]+" || echo "Aucune")
        info "Migration actuelle: $current_migration"
    else
        warn "Impossible de déterminer l'état des migrations (première installation ?)"
    fi
    
    # 2. Lister les migrations existantes
    log "📜 Liste des fichiers de migration existants:"
    local existing_migrations=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend find /app/alembic/versions -name "*.py" -type f 2>/dev/null | wc -l || echo "0")
    info "Nombre de fichiers de migration: $existing_migrations"
    
    if [ "$existing_migrations" -gt 0 ]; then
        log "📄 Fichiers de migration présents:"
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend ls -la /app/alembic/versions/ 2>/dev/null || true
    fi
    
    # 3. Génération automatique d'une migration si des changements sont détectés
    log "🔍 Vérification des changements de schéma et génération de migration..."
    local migration_name="auto_migrate_$(date +%Y%m%d_%H%M%S)"
    
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic revision --autogenerate -m "$migration_name" >/dev/null 2>&1; then
        info "✅ Commande de génération de migration exécutée"
        
        # Vérifier si une nouvelle migration a vraiment été créée
        local new_migrations=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend find /app/alembic/versions -name "*.py" -type f 2>/dev/null | wc -l || echo "0")
        
        if [ "$new_migrations" -gt "$existing_migrations" ]; then
            log "🆕 Nouvelle migration générée!"
            
            # Afficher la nouvelle migration créée
            log "📄 Nouvelle migration créée:"
            $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend ls -la /app/alembic/versions/ | tail -1 || true
            
            # Afficher le contenu de la nouvelle migration pour vérification
            log "📝 Contenu de la nouvelle migration:"
            local newest_migration=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend find /app/alembic/versions -name "*.py" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2 || "")
            if [ -n "$newest_migration" ]; then
                echo "----------------------------------------"
                $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend cat "$newest_migration" 2>/dev/null | head -50 || true
                echo "----------------------------------------"
            fi
        else
            info "ℹ️ Aucun changement de schéma détecté - pas de nouvelle migration"
        fi
    else
        warn "⚠️ Erreur lors de la génération de migration (peut être normal si aucun changement)"
    fi
    
    # 4. Application des migrations en attente
    log "⬆️ Application des migrations en attente..."
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic upgrade head; then
        info "✅ Migrations appliquées avec succès"
        
        # Vérifier l'état après application
        local new_current_migration=""
        if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic current >/dev/null 2>&1; then
            new_current_migration=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic current 2>/dev/null | grep -E "^[a-f0-9]+" || echo "Aucune")
            info "Nouvelle migration actuelle: $new_current_migration"
            
            if [ "$current_migration" != "$new_current_migration" ]; then
                info "🔄 Migration mise à jour de '$current_migration' vers '$new_current_migration'"
            else
                info "📌 Aucune nouvelle migration appliquée"
            fi
        fi
        
    else
        error "❌ Échec de l'application des migrations"
    fi
    
    # 5. Vérification que les champs sont maintenant présents dans la table users
    log "🔍 Vérification de la structure de la table users..."
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres psql -U "${POSTGRES_USER:-ajt_user}" -d "${POSTGRES_DB:-ajt_db}" -c "\d users" >/dev/null 2>&1; then
        info "📋 Structure actuelle de la table users:"
        echo "----------------------------------------"
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres psql -U "${POSTGRES_USER:-ajt_user}" -d "${POSTGRES_DB:-ajt_db}" -c "\d users" 2>/dev/null || true
        echo "----------------------------------------"
    else
        warn "⚠️ Impossible d'afficher la structure de la table users"
    fi
    
    # 6. Affichage de l'historique des migrations
    log "📜 Historique des migrations:"
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic history --indicate-current >/dev/null 2>&1; then
        echo "----------------------------------------"
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic history --indicate-current 2>/dev/null | head -20 || true
        echo "----------------------------------------"
    else
        # Alternative si la commande précédente échoue
        log "📜 Liste des migrations disponibles:"
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend find /app/alembic/versions -name "*.py" -type f | head -10 2>/dev/null || warn "Impossible d'afficher les migrations"
    fi
    
    log "✅ Gestion des migrations Alembic terminée avec succès"
}

# Vérification de la santé de l'application
health_check() {
    log "🏥 Vérification de la santé de l'application..."
    
    # URLs à tester (adaptez selon votre configuration)
    local frontend_url="http://localhost:3000"
    local backend_url="http://localhost:8000"
    
    # Test du frontend
    log "🌐 Test du frontend..."
    for i in {1..10}; do
        if curl -f -s "$frontend_url" > /dev/null; then
            info "✅ Frontend accessible !"
            break
        fi
        if [ $i -eq 10 ]; then
            error "❌ Frontend inaccessible après 10 tentatives"
        fi
        warn "Tentative $i/10 - Frontend en cours de démarrage..."
        sleep 10
    done
    
    # Test du backend
    log "🔧 Test du backend..."
    for i in {1..10}; do
        if curl -f -s "$backend_url/health" > /dev/null 2>&1 || curl -f -s "$backend_url" > /dev/null 2>&1; then
            info "✅ Backend accessible !"
            break
        fi
        if [ $i -eq 10 ]; then
            warn "⚠️ Backend inaccessible (vérifiez manuellement)"
            break
        fi
        warn "Tentative $i/10 - Backend en cours de démarrage..."
        sleep 10
    done
    
    # Vérification de la base de données
    log "🗄️ Test de la base de données..."
    if docker exec postgres_prod pg_isready -U ajt_user -d ajt_db > /dev/null 2>&1; then
        info "✅ Base de données accessible !"
    else
        warn "⚠️ Base de données inaccessible (vérifiez manuellement)"
    fi
}

# Rollback en cas d'échec
rollback() {
    error "💥 Échec du déploiement, rollback en cours..."
    
    if [ -f "$BACKUP_DIR/app_backup.tar.gz" ]; then
        log "🔄 Restauration de la version précédente..."
        
        cd "$(dirname "$APP_DIR")"
        rm -rf "$APP_DIR"
        tar -xzf "$BACKUP_DIR/app_backup.tar.gz"
        
        cd "$APP_DIR"
        manage_docker_containers
        
        warn "⚠️ Rollback terminé - Vérifiez l'état de l'application"
        warn "⚠️ ATTENTION: Les migrations de base de données ne peuvent pas être annulées automatiquement"
        warn "⚠️ Vous devrez peut-être restaurer manuellement la base de données depuis une sauvegarde"
    else
        error "❌ Impossible de faire le rollback - Pas de sauvegarde disponible"
    fi
}

# Nettoyage des anciennes sauvegardes
cleanup_old_backups() {
    log "🧹 Nettoyage des anciennes sauvegardes de déploiement..."
    
    local backup_base_dir="/home/ubuntu/backups_ajtpro/deployments"
    if [ -d "$backup_base_dir" ]; then
        find "$backup_base_dir" -maxdepth 1 -type d -name "20*" | sort -r | tail -n +6 | xargs rm -rf 2>/dev/null || true
        info "✅ Nettoyage terminé (conservation des 5 dernières)"
    fi
}

# Affichage des informations post-déploiement
show_deployment_info() {
    log "📋 Informations de déploiement:"
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "🌐 Frontend: http://$(hostname -I | awk '{print $1}'):3000"
    echo "🔧 Backend:  http://$(hostname -I | awk '{print $1}'):8000"
    echo "🗄️ Database: PostgreSQL sur le port 5432"
    echo "📝 Logs: docker compose logs -f [service_name]"
    echo "📊 Statut: docker compose ps"
    echo "🗃️ Migrations: docker compose exec backend alembic current"
    echo "╚═══════════════════════════════════════════════════════╝"
    
    # Informations Git
    cd "$APP_DIR"
    local commit_hash=$(git rev-parse --short HEAD)
    local branch=$(git branch --show-current)
    local commit_date=$(git log -1 --format=%cd --date=short)
    
    echo "📝 Version déployée:"
    echo "   Branche: $branch"
    echo "   Commit:  $commit_hash"
    echo "   Date:    $commit_date"
    
    # Informations sur les migrations
    log "🗃️ État des migrations:"
    if [ -n "${DOCKER_COMPOSE_CMD:-}" ] && [ -n "${COMPOSE_FILE:-}" ]; then
        local migration_info=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic current 2>/dev/null || echo "Informations non disponibles")
        echo "   $migration_info"
        
        # Afficher le nombre total de migrations
        local total_migrations=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend find /app/alembic/versions -name "*.py" -type f | wc -l 2>/dev/null || echo "0")
        echo "   Nombre total de fichiers de migration: $total_migrations"
    fi
    
    echo "╚═══════════════════════════════════════════════════════╝"
}

# Fonction principale
main() {
    log "🚀 Début du déploiement automatisé AJT Pro"
    
    # Trap pour gérer les erreurs et faire un rollback
    trap rollback ERR
    
    check_prerequisites
    setup_docker_network
    backup_database
    backup_current_version
    fetch_code
    build_frontend
    manage_docker_containers
    run_database_migrations  # AMÉLIORÉ : Gestion robuste des migrations Alembic
    health_check
    cleanup_old_backups
    show_deployment_info
    
    log "🎉 Déploiement terminé avec succès !"
    info "⏰ Durée totale: $SECONDS secondes"
}

# Gestion des arguments
case "${1:-}" in
    -h|--help)
        echo "Usage: $0 [branche] [options]"
        echo ""
        echo "Options:"
        echo "  -h, --help    Affiche cette aide"
        echo "  --no-backup   Skip la sauvegarde de la DB"
        echo "  --force       Force le déploiement sans confirmation"
        echo ""
        echo "Exemples:"
        echo "  $0                # Déploie la branche main"
        echo "  $0 develop        # Déploie la branche develop"
        echo "  $0 feature/new    # Déploie une branche spécifique"
        echo ""
        echo "Le script inclut maintenant la gestion automatique des migrations Alembic:"
        echo "  - Génération automatique de migrations si nécessaire"
        echo "  - Application des migrations en attente"
        echo "  - Vérification de l'état des migrations"
        echo "  - Affichage de la structure des tables"
        echo "  - Vérification robuste de la base de données"
        exit 0
        ;;
    --version)
        echo "AJT Pro Deploy Script v2.3 (avec support Alembic amélioré)"
        exit 0
        ;;
    *)
        # Confirmation avant déploiement en production
        if [ "${1:-main}" = "main" ] || [ "${1:-main}" = "master" ]; then
            echo ""
            warn "⚠️ Vous êtes sur le point de déployer en PRODUCTION"
            warn "⚠️ Les migrations de base de données seront appliquées automatiquement"
            read -p "Êtes-vous sûr de vouloir continuer? (oui/non): " confirmation
            if [ "$confirmation" != "oui" ]; then
                log "Déploiement annulé par l'utilisateur"
                exit 0
            fi
        fi
        
        main "$@"
        ;;
esac