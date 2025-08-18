#!/bin/bash

# Gestionnaire de services AJT Pro
# Usage: ./manage-services.sh [action] [service]

set -e

APP_DIR="/home/ubuntu/ajtpro"
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

# Déterminer la commande docker-compose
if command -v "docker compose" &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

cd "$APP_DIR"

# Fonctions de gestion des services
show_status() {
    log "📊 Statut des services AJT Pro:"
    echo "════════════════════════════════════════"
    $DOCKER_COMPOSE_CMD ps
    echo ""
    
    # Informations détaillées
    echo "🔍 Informations détaillées:"
    echo "Frontend:   http://$(hostname -I | awk '{print $1}'):3000"
    echo "Backend:    http://$(hostname -I | awk '{print $1}'):8000"
    echo "Database:   PostgreSQL sur port 5432"
    echo ""
    
    # Test de connectivité
    echo "🏥 Tests de connectivité:"
    if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Frontend accessible"
    else
        echo "❌ Frontend inaccessible"
    fi
    
    if curl -f -s http://localhost:8000 > /dev/null 2>&1; then
        echo "✅ Backend accessible"
    else
        echo "❌ Backend inaccessible"
    fi
    
    if docker exec postgres pg_isready -U ajt_user -d ajt_db > /dev/null 2>&1; then
        echo "✅ Database accessible"
    else
        echo "❌ Database inaccessible"
    fi
}

start_services() {
    local service="$1"
    if [ -n "$service" ]; then
        log "🚀 Démarrage du service: $service"
        $DOCKER_COMPOSE_CMD up -d "$service"
    else
        log "🚀 Démarrage de tous les services"
        $DOCKER_COMPOSE_CMD up -d
    fi
}

stop_services() {
    local service="$1"
    if [ -n "$service" ]; then
        log "⏹️  Arrêt du service: $service"
        $DOCKER_COMPOSE_CMD stop "$service"
    else
        log "⏹️  Arrêt de tous les services"
        $DOCKER_COMPOSE_CMD stop
    fi
}

restart_services() {
    local service="$1"
    if [ -n "$service" ]; then
        log "🔄 Redémarrage du service: $service"
        $DOCKER_COMPOSE_CMD restart "$service"
    else
        log "🔄 Redémarrage de tous les services"
        $DOCKER_COMPOSE_CMD restart
    fi
}

rebuild_services() {
    local service="$1"
    if [ -n "$service" ]; then
        log "🔨 Reconstruction du service: $service"
        $DOCKER_COMPOSE_CMD stop "$service"
        $DOCKER_COMPOSE_CMD build --no-cache "$service"
        $DOCKER_COMPOSE_CMD up -d "$service"
    else
        log "🔨 Reconstruction de tous les services"
        $DOCKER_COMPOSE_CMD down
        $DOCKER_COMPOSE_CMD build --no-cache
        $DOCKER_COMPOSE_CMD up -d
    fi
}

show_logs() {
    local service="$1"
    local lines="${2:-50}"
    
    if [ -n "$service" ]; then
        log "📋 Logs du service: $service (dernières $lines lignes)"
        $DOCKER_COMPOSE_CMD logs --tail="$lines" -f "$service"
    else
        log "📋 Logs de tous les services (dernières $lines lignes)"
        $DOCKER_COMPOSE_CMD logs --tail="$lines" -f
    fi
}

exec_shell() {
    local service="$1"
    
    case "$service" in
        frontend|ajt_frontend)
            log "🖥️  Connexion au container frontend..."
            docker exec -it ajt_frontend /bin/sh
            ;;
        backend|ajt_backend)
            log "🖥️  Connexion au container backend..."
            docker exec -it ajt_backend /bin/bash
            ;;
        postgres|database|db)
            log "🗄️  Connexion à PostgreSQL..."
            docker exec -it postgres psql -U ajt_user -d ajt_db
            ;;
        *)
            error "Service non reconnu. Services disponibles: frontend, backend, postgres"
            ;;
    esac
}

show_help() {
    echo "Gestionnaire de services AJT Pro"
    echo ""
    echo "Usage: $0 [action] [service] [options]"
    echo ""
    echo "Actions:"
    echo "  status, ps           Affiche le statut des services"
    echo "  start [service]      Démarre un service ou tous"
    echo "  stop [service]       Arrête un service ou tous"
    echo "  restart [service]    Redémarre un service ou tous"
    echo "  rebuild [service]    Reconstruit un service ou tous"
    echo "  logs [service] [n]   Affiche les logs (n=nombre de lignes)"
    echo "  shell [service]      Ouvre un shell dans le container"
    echo "  cleanup              Nettoie les ressources Docker"
    echo "  update               Met à jour et redémarre"
    echo ""
    echo "Services disponibles:"
    echo "  frontend, backend, postgres"
    echo ""
    echo "Exemples:"
    echo "  $0 status                    # Statut de tous les services"
    echo "  $0 restart backend           # Redémarre uniquement le backend"
    echo "  $0 logs frontend 100         # 100 dernières lignes du frontend"
    echo "  $0 shell postgres            # Shell PostgreSQL"
    echo "  $0 rebuild                   # Reconstruit tout"
}

cleanup_docker() {
    log "🧹 Nettoyage des ressources Docker..."
    
    # Arrêt des services
    $DOCKER_COMPOSE_CMD down --remove-orphans
    
    # Nettoyage des images et volumes non utilisés
    docker system prune -f
    docker volume prune -f
    
    # Redémarrage
    $DOCKER_COMPOSE_CMD up -d
    
    info "✅ Nettoyage terminé"
}

update_and_restart() {
    log "🔄 Mise à jour et redémarrage..."
    
    # Mise à jour du code
    git fetch origin
    git pull origin main
    
    # Reconstruction et redémarrage
    $DOCKER_COMPOSE_CMD down
    $DOCKER_COMPOSE_CMD build --no-cache
    $DOCKER_COMPOSE_CMD up -d
    
    info "✅ Mise à jour terminée"
}

# Gestion des arguments
case "${1:-status}" in
    status|ps)
        show_status
        ;;
    start)
        start_services "$2"
        ;;
    stop)
        stop_services "$2"
        ;;
    restart)
        restart_services "$2"
        ;;
    rebuild)
        rebuild_services "$2"
        ;;
    logs)
        show_logs "$2" "$3"
        ;;
    shell|exec)
        exec_shell "$2"
        ;;
    cleanup)
        cleanup_docker
        ;;
    update)
        update_and_restart
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        warn "Action non reconnue: $1"
        show_help
        exit 1
        ;;
esac