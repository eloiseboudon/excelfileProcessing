#!/bin/bash

# Script pour exécuter des scripts Python dans le container backend
# Usage: ./run_script.sh [script_name] [options]

set -e  # Arrêt du script en cas d'erreur

# Configuration - Adaptation automatique selon le répertoire
DOCKER_COMPOSE_FILE="docker-compose.yml"
DOCKER_COMPOSE_DEV_FILE="docker-compose.override.yml"
DOCKER_COMPOSE_PROD_FILE="docker-compose.prod.yml"
BACKEND_PATH="backend"
SCRIPT_NAME="${1}"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
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

success() {
    echo -e "${CYAN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

# Fonction d'aide
show_help() {
    echo -e "${PURPLE}===============================================${NC}"
    echo -e "${PURPLE}   🚀 Script d'exécution pour containers    ${NC}"
    echo -e "${PURPLE}===============================================${NC}"
    echo ""
    echo "Usage: $0 [script_name] [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Affiche cette aide"
    echo "  -f, --file <file>       Utilise un fichier docker-compose spécifique"
    echo "  -s, --script <script>   Nom du script Python à exécuter"
    echo "  --dev                   Force l'utilisation de l'environnement de développement"
    echo "  --prod                  Force l'utilisation de l'environnement de production"
    echo "  --dry-run               Affiche la commande sans l'exécuter"
    echo "  --show-env              Affiche les variables d'environnement du container"
    echo "  --logs                  Affiche les logs du backend avant d'exécuter"
    echo "  --cleanup               Supprime le script du container après exécution"
    echo ""
    echo "Exemples:"
    echo "  $0 ram_norme.py                          # Exécution avec sélection d'environnement"
    echo "  $0 ram_norme.py --dev                    # Force l'environnement de développement"
    echo "  $0 ram_norme.py --prod                   # Force l'environnement de production"
    echo "  $0 -s mon_script.py --dry-run            # Affiche juste la commande"
    echo "  $0 database/ram_norme.py --dev           # Script dans un sous-répertoire"
    echo ""
}

# Sélection de l'environnement
select_environment() {
    # Si déjà forcé par les paramètres, ne pas demander
    if [ "$FORCE_DEV" = "true" ] || [ "$FORCE_PROD" = "true" ]; then
        return 0
    fi
    
    echo -e "${PURPLE}===============================================${NC}"
    echo -e "${PURPLE}   🌍 Sélection de l'environnement          ${NC}"
    echo -e "${PURPLE}===============================================${NC}"
    echo ""
    echo -e "${CYAN}Dans quel environnement voulez-vous exécuter le script ?${NC}"
    echo ""
    echo -e "${GREEN}1)${NC} 🖥️  Développement (localhost) - docker-compose.override.yml"
    echo -e "${RED}2)${NC} 🌐 Production - docker-compose.prod.yml"
    echo -e "${YELLOW}3)${NC} ⚙️  Base (docker-compose.yml)"
    echo ""
    
    while true; do
        read -p "Votre choix (1/2/3): " env_choice
        case $env_choice in
            1)
                USE_DEV=true
                info "🖥️  Environnement de développement sélectionné"
                break
                ;;
            2)
                USE_PROD=true
                info "🌐 Environnement de production sélectionné"
                break
                ;;
            3)
                USE_BASE=true
                info "⚙️  Environnement de base sélectionné"
                break
                ;;
            *)
                warn "Choix invalide. Veuillez sélectionner 1, 2 ou 3."
                ;;
        esac
    done
    echo ""
}

# Détection de la commande docker-compose
detect_docker_compose() {
    DOCKER_COMPOSE_CMD="docker compose"
    info "Utilisation de: $DOCKER_COMPOSE_CMD"
}

# Sélection du fichier docker-compose
select_compose_file() {
    local compose_files=""
    
    # Déterminer les fichiers à utiliser selon l'environnement
    if [ "$FORCE_DEV" = "true" ] || [ "$USE_DEV" = "true" ]; then
        if [ -f "$DOCKER_COMPOSE_FILE" ] && [ -f "$DOCKER_COMPOSE_DEV_FILE" ]; then
            compose_files="-f $DOCKER_COMPOSE_FILE -f $DOCKER_COMPOSE_DEV_FILE"
            info "🖥️  Utilisation de l'environnement de développement"
            info "   - Fichier de base: $DOCKER_COMPOSE_FILE"
            info "   - Fichier dev: $DOCKER_COMPOSE_DEV_FILE"
        else
            error "Fichiers de développement introuvables"
        fi
    elif [ "$FORCE_PROD" = "true" ] || [ "$USE_PROD" = "true" ]; then
        if [ -f "$DOCKER_COMPOSE_PROD_FILE" ]; then
            compose_files="-f $DOCKER_COMPOSE_PROD_FILE"
            info "🌐 Utilisation de l'environnement de production: $DOCKER_COMPOSE_PROD_FILE"
        else
            error "Fichier de production $DOCKER_COMPOSE_PROD_FILE introuvable"
        fi
    elif [ "$USE_BASE" = "true" ]; then
        if [ -f "$DOCKER_COMPOSE_FILE" ]; then
            compose_files="-f $DOCKER_COMPOSE_FILE"
            info "⚙️  Utilisation du fichier de base: $DOCKER_COMPOSE_FILE"
        else
            error "Fichier de base $DOCKER_COMPOSE_FILE introuvable"
        fi
    elif [ -n "$CUSTOM_COMPOSE_FILE" ]; then
        if [ -f "$CUSTOM_COMPOSE_FILE" ]; then
            compose_files="-f $CUSTOM_COMPOSE_FILE"
            info "📁 Utilisation du fichier personnalisé: $CUSTOM_COMPOSE_FILE"
        else
            error "Fichier docker-compose personnalisé $CUSTOM_COMPOSE_FILE introuvable"
        fi
    else
        error "Aucun environnement sélectionné"
    fi
    
    export COMPOSE_FILES="$compose_files"
}

# Vérification des prérequis
check_prerequisites() {
    log "🔍 Vérification des prérequis..."
    
    # Rechercher le script dans plusieurs emplacements
    local script_locations=(
        "$SCRIPT_NAME"  # Répertoire courant
        "backend/scripts/$SCRIPT_NAME"  # Dans backend/scripts
        "backend/scripts/database/$SCRIPT_NAME"  # Dans database
        "backend/scripts/migration/$SCRIPT_NAME"  # Dans migration
        "backend/scripts/maintenance/$SCRIPT_NAME"  # Dans maintenance
    )
    
    local found_script=""
    info "🔍 Recherche du script '$SCRIPT_NAME' dans les emplacements suivants:"
    
    for location in "${script_locations[@]}"; do
        info "   📂 Vérification: $location"
        if [ -f "$location" ]; then
            found_script="$location"
            success "✅ Script trouvé dans: $location"
            break
        else
            info "   ❌ Non trouvé: $location"
        fi
    done
    
    if [ -z "$found_script" ]; then
        error "❌ Script $SCRIPT_NAME introuvable dans tous les emplacements vérifiés:
  - Répertoire courant: $SCRIPT_NAME
  - Scripts backend: backend/scripts/$SCRIPT_NAME
  - Scripts database: backend/scripts/database/$SCRIPT_NAME
  - Scripts migration: backend/scripts/migration/$SCRIPT_NAME
  - Scripts maintenance: backend/scripts/maintenance/$SCRIPT_NAME

💡 Vérifiez que le script existe dans l'un de ces emplacements."
    fi
    
    # Mettre à jour SCRIPT_NAME avec le chemin trouvé
    SCRIPT_NAME="$found_script"
    
    # Vérifier que les fichiers docker-compose existent
    for file in $(echo $COMPOSE_FILES | sed 's/-f //g'); do
        if [ ! -f "$file" ]; then
            error "Fichier docker-compose $file introuvable"
        fi
    done
    
    # Vérifier que le container backend existe et fonctionne
    if ! $DOCKER_COMPOSE_CMD $COMPOSE_FILES ps backend | grep -q "Up"; then
        warn "Le container backend ne semble pas être en cours d'exécution"
        log "📊 Statut des containers:"
        $DOCKER_COMPOSE_CMD $COMPOSE_FILES ps
        
        echo ""
        read -p "Voulez-vous démarrer les containers maintenant ? (y/N): " start_containers
        if [[ $start_containers =~ ^[Yy]$ ]]; then
            log "🚀 Démarrage des containers..."
            $DOCKER_COMPOSE_CMD $COMPOSE_FILES up -d
            sleep 5
            
            # Vérifier à nouveau
            if ! $DOCKER_COMPOSE_CMD $COMPOSE_FILES ps backend | grep -q "Up"; then
                error "Impossible de démarrer le container backend"
            fi
        else
            error "Container backend requis pour exécuter le script"
        fi
    fi
    
    success "✅ Tous les prérequis sont satisfaits"
}

# Affichage des variables d'environnement
show_environment() {
    log "🌍 Variables d'environnement du container backend:"
    echo "──────────────────────────────────────────────────"
    $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec backend env | grep -E "(DATABASE_|DB_|POSTGRES_|FLASK_)" | sort
    echo "──────────────────────────────────────────────────"
}

# Affichage des logs
show_logs() {
    log "📋 Logs récents du backend:"
    echo "──────────────────────────────────────────────────"
    $DOCKER_COMPOSE_CMD $COMPOSE_FILES logs --tail=20 backend
    echo "──────────────────────────────────────────────────"
}

# Test de connexion à la base de données
test_database_connection() {
    log "🔌 Test de connexion à la base de données..."
    
    if $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T backend python -c "
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
        success "✅ Base de données accessible"
    else
        error "❌ Impossible de se connecter à la base de données"
    fi
}

# Copie du script dans le container
copy_script_to_container() {
    log "📋 Préparation du script pour exécution..."
    
    # Le script a déjà été trouvé dans check_prerequisites
    info "📁 Script source: $SCRIPT_NAME"
    
    # Extraire juste le nom du fichier pour la destination
    local script_basename=$(basename "$SCRIPT_NAME")
    local container_path="scripts/$script_basename"
    
    # Déterminer le sous-répertoire si le script vient d'un dossier spécialisé
    if [[ "$SCRIPT_NAME" == *"/database/"* ]]; then
        container_path="scripts/database/$script_basename"
    elif [[ "$SCRIPT_NAME" == *"/migration/"* ]]; then
        container_path="scripts/migration/$script_basename"
    elif [[ "$SCRIPT_NAME" == *"/maintenance/"* ]]; then
        container_path="scripts/maintenance/$script_basename"
    fi
    
    info "📁 Chemin de destination: $container_path"
    
    # Si le script est déjà dans backend/scripts/, on peut directement vérifier s'il est accessible
    if [[ "$SCRIPT_NAME" == backend/scripts/* ]]; then
        info "📁 Script déjà dans le volume partagé backend/scripts"
        
        # Vérifier que le script est accessible dans le container
        if $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T backend test -f "$container_path"; then
            success "✅ Script accessible dans le container via le volume"
            # Mettre à jour SCRIPT_NAME pour l'exécution
            SCRIPT_NAME="$container_path"
            return 0
        else
            warn "⚠️ Script non accessible dans le container, tentative de copie..."
        fi
    fi
    
    # Si le volume partagé ne fonctionne pas, utiliser docker cp
    info "📤 Utilisation de docker cp pour la copie..."
    
    local container_name=$($DOCKER_COMPOSE_CMD $COMPOSE_FILES ps -q backend)
    if [ -n "$container_name" ]; then
        info "📁 Container trouvé: $container_name"
        
        # Créer le répertoire dans le container
        local container_dir=$(dirname "/app/$container_path")
        $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T backend mkdir -p "$container_dir"
        
        # Nettoyer les anciennes copies
        $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T backend rm -f "/app/$container_path" "/tmp/$script_basename" 2>/dev/null || true
        
        # Copie directe vers le bon emplacement
        if docker cp "$SCRIPT_NAME" "$container_name:/app/$container_path"; then
            success "✅ Script copié vers /app/$container_path"
            
            if $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T backend test -f "/app/$container_path"; then
                success "✅ Script présent dans /app/$container_path"
                # Mettre à jour SCRIPT_NAME pour l'exécution
                SCRIPT_NAME="$container_path"
            else
                error "❌ Script non trouvé après copie"
            fi
        else
            error "❌ Échec de la copie du script"
        fi
    else
        error "❌ Container backend introuvable"
    fi
}

# Exécution du script principal
execute_script() {
    log "🐍 Exécution du script Python: $SCRIPT_NAME"
    
    # Construction de la commande (SCRIPT_NAME contient déjà le bon chemin)
    local cmd="$DOCKER_COMPOSE_CMD $COMPOSE_FILES exec backend python $SCRIPT_NAME"
    
    if [ "$DRY_RUN" = "true" ]; then
        echo ""
        info "🔍 Commande qui serait exécutée:"
        echo "   $cmd"
        echo ""
        return 0
    fi
    
    echo "──────────────────────────────────────────────────"
    echo "🚀 Début de l'exécution..."
    echo "──────────────────────────────────────────────────"
    
    # Exécution effective
    if $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec backend python "$SCRIPT_NAME"; then
        echo "──────────────────────────────────────────────────"
        success "✅ Script exécuté avec succès !"
    else
        echo "──────────────────────────────────────────────────"
        error "❌ Échec de l'exécution du script"
    fi
}

# Nettoyage après exécution
cleanup() {
    if [ "$CLEANUP_SCRIPT" = "true" ]; then
        log "🧹 Nettoyage du script dans le container..."
        # Ne supprimer que si le script n'est PAS dans le volume partagé backend/scripts/
        # Cela évite de supprimer le fichier source
        if [[ "$SCRIPT_NAME" == scripts/* ]]; then
            # C'est une copie dans le container, on peut la supprimer
            $DOCKER_COMPOSE_CMD $COMPOSE_FILES exec -T backend rm -f "$SCRIPT_NAME" 2>/dev/null || true
        else
            info "🛡️ Fichier source préservé (pas de nettoyage du volume partagé)"
        fi
    fi
}

# Fonction principale
main() {
    echo -e "${PURPLE}===============================================${NC}"
    echo -e "${PURPLE}   🚀 Démarrage de l'exécution du script    ${NC}"
    echo -e "${PURPLE}===============================================${NC}"
    echo ""
    
    detect_docker_compose
    select_environment
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
    
    echo ""
    success "🎉 Terminé !"
}

# Gestion des arguments
DRY_RUN=false
SHOW_ENV=false
SHOW_LOGS=false
FORCE_DEV=false
FORCE_PROD=false
USE_DEV=false
USE_PROD=false
USE_BASE=false
CLEANUP_SCRIPT=false
CUSTOM_COMPOSE_FILE=""

# Si le premier argument n'est pas une option, c'est le nom du script
if [[ $# -gt 0 && ! "$1" =~ ^- ]]; then
    SCRIPT_NAME="$1"
    shift
fi

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
        --dev)
            FORCE_DEV=true
            shift
            ;;
        --prod)
            FORCE_PROD=true
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

# Vérifier qu'un script est spécifié
if [ -z "$SCRIPT_NAME" ]; then
    error "Aucun script spécifié. Utilisez: $0 <nom_du_script.py> [options]"
fi

# Trap pour le nettoyage en cas d'erreur
trap cleanup EXIT

# Confirmation avant exécution du script
echo -e "${CYAN}Vous allez lancer le script: ${YELLOW}$SCRIPT_NAME${NC}"
read -p "Continuer ? (oui/non): " confirmation
if [ "$confirmation" != "oui" ]; then
    log "Exécution annulée par l'utilisateur"
    exit 0
fi

echo ""
main "$@"