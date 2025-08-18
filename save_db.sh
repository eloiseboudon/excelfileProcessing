#!/bin/bash

# Script de sauvegarde de la base de données PostgreSQL
# Usage: ./save_db.sh [nom_sauvegarde_optionnel]

set -e  # Arrêt du script en cas d'erreur

# Configuration
CONTAINER_NAME="postgres"
DB_NAME="ajt_db"
DB_USER="ajt_user"
DB_PASSWORD="ajt_password"
BACKUP_DIR="/home/ubuntu/backups/database"
MAX_BACKUPS=10  # Nombre maximum de sauvegardes à conserver

# Couleurs pour les logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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
    
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    # Vérifier que le container PostgreSQL est en cours d'exécution
    if ! docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
        error "Le container PostgreSQL '$CONTAINER_NAME' n'est pas en cours d'exécution"
    fi
    
    log "Container PostgreSQL trouvé et actif"
}

# Création du répertoire de sauvegarde
create_backup_directory() {
    if [ ! -d "$BACKUP_DIR" ]; then
        log "Création du répertoire de sauvegarde: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

# Génération du nom de fichier de sauvegarde
generate_backup_filename() {
    local custom_name="$1"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    if [ -n "$custom_name" ]; then
        echo "${custom_name}_${timestamp}"
    else
        echo "ajt_db_backup_${timestamp}"
    fi
}

# Sauvegarde de la base de données
backup_database() {
    local backup_name="$1"
    local sql_file="${BACKUP_DIR}/${backup_name}.sql"
    local tar_file="${BACKUP_DIR}/${backup_name}.tar.gz"
    
    log "Début de la sauvegarde de la base de données '$DB_NAME'..."
    
    # Export de la base de données avec pg_dump
    log "Création du dump SQL..."
    docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
        pg_dump -h localhost -U "$DB_USER" -d "$DB_NAME" \
        --verbose --clean --no-owner --no-privileges \
        > "$sql_file"
    
    if [ ! -f "$sql_file" ] || [ ! -s "$sql_file" ]; then
        error "Échec de la création du dump SQL ou fichier vide"
    fi
    
    log "Dump SQL créé: $(du -h "$sql_file" | cut -f1)"
    
    # Compression en tar.gz
    log "Compression du dump en tar.gz..."
    tar -czf "$tar_file" -C "$BACKUP_DIR" "$(basename "$sql_file")"
    
    if [ ! -f "$tar_file" ]; then
        error "Échec de la compression tar.gz"
    fi
    
    # Suppression du fichier SQL temporaire
    rm -f "$sql_file"
    
    log "Sauvegarde terminée: $tar_file"
    log "Taille de la sauvegarde: $(du -h "$tar_file" | cut -f1)"
    
    echo "$tar_file"
}

# Vérification de l'intégrité de la sauvegarde
verify_backup() {
    local tar_file="$1"
    
    log "Vérification de l'intégrité de la sauvegarde..."
    
    if tar -tzf "$tar_file" >/dev/null 2>&1; then
        log "✅ Sauvegarde valide et lisible"
    else
        error "❌ Sauvegarde corrompue ou illisible"
    fi
}

# Nettoyage des anciennes sauvegardes
cleanup_old_backups() {
    log "Nettoyage des anciennes sauvegardes (conservation des $MAX_BACKUPS dernières)..."
    
    local backup_count=$(find "$BACKUP_DIR" -name "*.tar.gz" -type f | wc -l)
    
    if [ "$backup_count" -gt "$MAX_BACKUPS" ]; then
        local files_to_delete=$((backup_count - MAX_BACKUPS))
        log "Suppression de $files_to_delete ancienne(s) sauvegarde(s)..."
        
        find "$BACKUP_DIR" -name "*.tar.gz" -type f -printf '%T@ %p\n' | \
        sort -n | \
        head -n "$files_to_delete" | \
        cut -d' ' -f2- | \
        while read -r file; do
            log "Suppression: $(basename "$file")"
            rm -f "$file"
        done
    else
        log "Aucune sauvegarde à supprimer ($backup_count/$MAX_BACKUPS)"
    fi
}

# Affichage des statistiques
show_backup_stats() {
    log "📊 Statistiques des sauvegardes:"
    echo "----------------------------------------"
    echo "Répertoire: $BACKUP_DIR"
    echo "Nombre total: $(find "$BACKUP_DIR" -name "*.tar.gz" -type f | wc -l)"
    echo "Espace utilisé: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "N/A")"
    echo "----------------------------------------"
    
    log "📁 Dernières sauvegardes:"
    find "$BACKUP_DIR" -name "*.tar.gz" -type f -printf '%TY-%Tm-%Td %TH:%TM - %f - %s bytes\n' | \
    sort -r | head -5 | while read -r line; do
        echo "  $line"
    done
}

# Test de restauration (optionnel)
test_restore() {
    local tar_file="$1"
    local test_db="${DB_NAME}_test_restore"
    
    log "🧪 Test de restauration (optionnel)..."
    
    # Extraction du dump
    local temp_dir=$(mktemp -d)
    tar -xzf "$tar_file" -C "$temp_dir"
    local sql_file=$(find "$temp_dir" -name "*.sql" | head -1)
    
    if [ -n "$sql_file" ]; then
        log "Test de restauration sur une base temporaire..."
        
        # Création d'une base de test
        docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            createdb -h localhost -U "$DB_USER" "$test_db" 2>/dev/null || true
        
        # Test de restauration
        if docker exec -i -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            psql -h localhost -U "$DB_USER" -d "$test_db" < "$sql_file" >/dev/null 2>&1; then
            log "✅ Test de restauration réussi"
        else
            warn "⚠️  Test de restauration échoué (cela peut être normal selon la structure de la DB)"
        fi
        
        # Nettoyage de la base de test
        docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            dropdb -h localhost -U "$DB_USER" "$test_db" 2>/dev/null || true
    fi
    
    # Nettoyage du répertoire temporaire
    rm -rf "$temp_dir"
}

# Fonction principale
main() {
    local custom_name="$1"
    
    log "🚀 Début de la sauvegarde de la base de données AJT"
    
    check_prerequisites
    create_backup_directory
    
    local backup_name=$(generate_backup_filename "$custom_name")
    local backup_file=$(backup_database "$backup_name")
    
    verify_backup "$backup_file"
    
    # Test de restauration (décommentez si souhaité)
    # test_restore "$backup_file"
    
    cleanup_old_backups
    show_backup_stats
    
    log "✅ Sauvegarde terminée avec succès!"
    log "📁 Fichier de sauvegarde: $backup_file"
    
    # Affichage du chemin pour faciliter la copie
    echo ""
    echo "Pour restaurer cette sauvegarde:"
    echo "tar -xzf $backup_file"
    echo "docker exec -i -e PGPASSWORD=\"$DB_PASSWORD\" $CONTAINER_NAME psql -h localhost -U $DB_USER -d $DB_NAME < nom_du_fichier.sql"
}

# Gestion des arguments
case "${1:-}" in
    -h|--help)
        echo "Usage: $0 [nom_sauvegarde_optionnel]"
        echo ""
        echo "Options:"
        echo "  -h, --help    Affiche cette aide"
        echo "  -s, --stats   Affiche uniquement les statistiques"
        echo ""
        echo "Exemples:"
        echo "  $0                    # Sauvegarde avec nom automatique"
        echo "  $0 migration_v2       # Sauvegarde avec nom personnalisé"
        exit 0
        ;;
    -s|--stats)
        create_backup_directory
        show_backup_stats
        exit 0
        ;;
    *)
        main "$1"
        ;;
esac