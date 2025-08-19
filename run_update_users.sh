#!/bin/bash

# Script pour exécuter update_users_table.py dans le container backend
# Usage: ./run_update_users.sh [options]

set -e  # Arrêt du script en cas d'erreur

# Configuration
DOCKER_COMPOSE_FILE="docker-compose.yml"
DOCKER_COMPOSE_PROD_FILE="docker-compose.prod.yml"
SCRIPT_NAME="update_users_table.py"

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

# Fonction d'aide
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Affiche cette aide"
    echo "  -f, --file <file>       Utilise un fichier docker-compose spécifique"
    echo "  -s, --script <script>   Nom du script Python à exécuter (défaut: $SCRIPT_NAME)"
    echo "  --prod                  Utilise le fichier docker-compose.prod.yml"
    echo "  --dry-run               Affiche la commande sans l'exécuter"
    echo "  --show-env              Affiche les variables d'environnement du container"
    echo "  --logs                  Affiche les logs du backend avant d'exécuter"
    echo ""
    echo "Exemples:"
    echo "  $0                                    # Exécution normale"
    echo "  $0 --prod                             # Utilise le fichier de production"
    echo "  $0 -s mon_script.py                   # Exécute un autre script"
    echo "  $0 --dry-run                          # Affiche juste la commande"
    echo "  $0 --show-env                         # Montre les variables d'environnement"
    echo ""
}

# Détection de la commande docker-compose
detect_docker_compose() {
DOCKER_COMPOSE_CMD="docker compose"
    
    info "Utilisation de: $DOCKER_COMPOSE_CMD"
}

# Sélection du fichier docker-compose
select_compose_file() {
    local compose_file="$DOCKER_COMPOSE_FILE"
    
    # Si le flag --prod est utilisé
    if [ "$USE_PROD" = "true" ]; then
        if [ -f "$DOCKER_COMPOSE_PROD_FILE" ]; then
            compose_file="$DOCKER_COMPOSE_PROD_FILE"
            info "Utilisation du fichier de production: $compose_file"
        else
            error "Fichier de production $DOCKER_COMPOSE_PROD_FILE introuvable"
        fi
    # Si un fichier spécifique est demandé
    elif [ -n "$CUSTOM_COMPOSE_FILE" ]; then
        if [ -f "$CUSTOM_COMPOSE_FILE" ]; then
            compose_file="$CUSTOM_COMPOSE_FILE"
            info "Utilisation du fichier personnalisé: $compose_file"
        else
            error "Fichier docker-compose personnalisé $CUSTOM_COMPOSE_FILE introuvable"
        fi
    # Détection automatique
    else
        if [ -f "$DOCKER_COMPOSE_PROD_FILE" ]; then
            read -p "Utiliser le fichier de production ? (y/N): " use_prod
            if [[ $use_prod =~ ^[Yy]$ ]]; then
                compose_file="$DOCKER_COMPOSE_PROD_FILE"
                info "Utilisation du fichier de production: $compose_file"
            fi
        fi
    fi
    
    export COMPOSE_FILE="$compose_file"
}

# Vérification des prérequis
check_prerequisites() {
    log "🔍 Vérification des prérequis..."
    
    # Vérifier que le fichier script existe
    if [ ! -f "$SCRIPT_NAME" ]; then
        error "Script $SCRIPT_NAME introuvable dans le répertoire courant"
    fi
    
    # Vérifier que docker-compose.yml existe
    if [ ! -f "$COMPOSE_FILE" ]; then
        error "Fichier docker-compose $COMPOSE_FILE introuvable"
    fi
    
    # Vérifier que le container backend existe et fonctionne
    if ! $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps backend | grep -q "Up"; then
        warn "Le container backend ne semble pas être en cours d'exécution"
        log "📊 Statut des containers:"
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps
        
        read -p "Voulez-vous démarrer les containers maintenant ? (y/N): " start_containers
        if [[ $start_containers =~ ^[Yy]$ ]]; then
            log "🚀 Démarrage des containers..."
            $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d
            sleep 5
        else
            error "Container backend requis pour exécuter le script"
        fi
    fi
    
    info "✅ Tous les prérequis sont satisfaits"
}

# Affichage des variables d'environnement
show_environment() {
    log "🌍 Variables d'environnement du container backend:"
    echo "────────────────────────────────────────────────────"
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec backend env | grep -E "(DATABASE_|DB_|POSTGRES_)" | sort
    echo "────────────────────────────────────────────────────"
}

# Affichage des logs
show_logs() {
    log "📋 Logs récents du backend:"
    echo "────────────────────────────────────────────────────"
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" logs --tail=20 backend
    echo "────────────────────────────────────────────────────"
}

# Test de connexion à la base de données
test_database_connection() {
    log "🔌 Test de connexion à la base de données..."
    
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend python -c "
import os, psycopg2
try:
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('❌ DATABASE_URL non définie')
        exit(1)
    conn = psycopg2.connect(db_url)
    conn.close()
    print('✅ Connexion à la base de données réussie')
    exit(0)
except Exception as e:
    print(f'❌ Erreur de connexion: {e}')
    exit(1)
"; then
        info "✅ Base de données accessible"
    else
        error "❌ Impossible de se connecter à la base de données"
    fi
}

# Exécution du script principal
execute_script() {
    log "🐍 Exécution du script Python: $SCRIPT_NAME"
    
    # Construction de la commande
    local cmd="$DOCKER_COMPOSE_CMD -f $COMPOSE_FILE exec backend python $SCRIPT_NAME"
    
    if [ "$DRY_RUN" = "true" ]; then
        echo ""
        info "🔍 Commande qui serait exécutée:"
        echo "   $cmd"
        echo ""
        return 0
    fi
    
    echo "────────────────────────────────────────────────────"
    echo "🚀 Début de l'exécution..."
    echo "────────────────────────────────────────────────────"
    
    # Exécution effective
    if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec backend python "$SCRIPT_NAME"; then
        echo "────────────────────────────────────────────────────"
        log "✅ Script exécuté avec succès !"
    else
        echo "────────────────────────────────────────────────────"
        error "❌ Échec de l'exécution du script"
    fi
}

# Copie du script dans le container (si nécessaire)
copy_script_to_container() {
    log "📋 Vérification de la présence du script dans le container..."
    
    # Vérifier si le script existe dans le container
    if ! $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend test -f "$SCRIPT_NAME" 2>/dev/null; then
        log "📤 Copie du script vers le container..."
        
        # Méthode 1: Utiliser docker cp
        local container_name=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps -q backend)
        if [ -n "$container_name" ]; then
            docker cp "$SCRIPT_NAME" "$container_name:/$SCRIPT_NAME"
            info "✅ Script copié avec succès"
        else
            error "❌ Impossible de trouver le container backend"
        fi
    else
        info "✅ Script déjà présent dans le container"
    fi
}

# Nettoyage après exécution
cleanup() {
    if [ "$CLEANUP_SCRIPT" = "true" ]; then
        log "🧹 Nettoyage du script dans le container..."
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend rm -f "$SCRIPT_NAME" 2>/dev/null || true
    fi
}

# Fonction principale
main() {
    log "🚀 Démarrage de l'exécution du script dans le container"
    
    detect_docker_compose
    select_compose_file
    check_prerequisites
    
    # Actions optionnelles
    if [ "$SHOW_ENV" = "true" ]; then
        show_environment
    fi
    
    if [ "$SHOW_LOGS" = "true" ]; then
        show_logs
    fi
    
    test_database_connection
    copy_script_to_container
    execute_script
    cleanup
    
    log "🎉 Terminé !"
}

# Gestion des arguments
DRY_RUN=false
SHOW_ENV=false
SHOW_LOGS=false
USE_PROD=false
CLEANUP_SCRIPT=false
CUSTOM_COMPOSE_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--file)
            CUSTOM_COMPOSE_FILE="$2"
            shift 2
            ;;
        -s|--script)
            SCRIPT_NAME="$2"
            shift 2
            ;;
        --prod)
            USE_PROD=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --show-env)
            SHOW_ENV=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --cleanup)
            CLEANUP_SCRIPT=true
            shift
            ;;
        *)
            error "Option inconnue: $1"
            ;;
    esac
done

# Trap pour le nettoyage en cas d'erreur
trap cleanup EXIT

# Exécution principale
main "$@"