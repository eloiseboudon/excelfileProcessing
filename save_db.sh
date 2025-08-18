#!/bin/bash

# Script de sauvegarde de la base de données PostgreSQL
# Usage: ./save_db.sh [nom_sauvegarde_optionnel]

set -e  # Arrêt du script en cas d'erreur

# Configuration
CONTAINER_NAME="postgres_prod"
DB_NAME="ajt_db"
DB_USER="ajt_user"
DB_PASSWORD="ajt_password"
BACKUP_DIR="/home/ubuntu/backups_ajtpro/database"
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
        # Essayer avec le nom alternatif
        if docker ps --format "table {{.Names}}" | grep -q "^postgres$"; then
            CONTAINER_NAME="postgres"
            log "Container PostgreSQL trouvé sous le nom 'postgres'"
        else
            error "Aucun container PostgreSQL trouvé (ni '$CONTAINER_NAME' ni 'postgres')"
        fi
    else
        log "Container PostgreSQL trouvé: $CONTAINER_NAME"
    fi
    
    # Test de connexion à la base de données
    if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
        log "✅ Connexion à la base de données confirmée"
    else
        warn "⚠️ Impossible de vérifier la connexion à la base de données"
    fi
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
    
    log "Début de la sauvegarde de la base de données '$DB_NAME'..." >&2
    
    # Export de la base de données avec pg_dump
    log "Création du dump SQL..." >&2
    
    # Méthode alternative plus robuste
    if docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
        pg_dump -h localhost -U "$DB_USER" -d "$DB_NAME" \
        --verbose --clean --no-owner --no-privileges \
        --format=custom --compress=9 > "${sql_file}.custom" 2>/dev/null; then
        
        log "Dump custom créé avec succès" >&2
        
        # Conversion en SQL standard pour compatibilité
        docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            pg_restore --no-owner --no-privileges --format=custom \
            --file=/tmp/dump.sql "${sql_file}.custom" 2>/dev/null || true
        
        docker exec "$CONTAINER_NAME" cat /tmp/dump.sql > "$sql_file" 2>/dev/null || {
            # Fallback: utiliser directement le dump custom comme fichier principal
            mv "${sql_file}.custom" "$sql_file"
            log "Utilisation du format custom PostgreSQL" >&2
        }
        
        # Nettoyage
        rm -f "${sql_file}.custom"
        docker exec "$CONTAINER_NAME" rm -f /tmp/dump.sql 2>/dev/null || true
        
    else
        # Méthode de fallback: dump SQL standard
        log "Utilisation de la méthode de sauvegarde alternative..." >&2
        docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            pg_dump -h localhost -U "$DB_USER" -d "$DB_NAME" \
            --clean --no-owner --no-privileges > "$sql_file" 2>/dev/null
    fi
    
    if [ ! -f "$sql_file" ] || [ ! -s "$sql_file" ]; then
        error "Échec de la création du dump SQL ou fichier vide"
    fi
    
    log "Dump SQL créé: $(du -h "$sql_file" | cut -f1)" >&2
    
    # Compression en tar.gz avec vérification
    log "Compression du dump en tar.gz..." >&2
    if tar -czf "$tar_file" -C "$BACKUP_DIR" "$(basename "$sql_file")" 2>/dev/null; then
        log "✅ Compression réussie" >&2
    else
        error "❌ Échec de la compression tar.gz"
    fi
    
    if [ ! -f "$tar_file" ] || [ ! -s "$tar_file" ]; then
        error "Fichier tar.gz manquant ou vide"
    fi
    
    # Suppression du fichier SQL temporaire
    rm -f "$sql_file"
    
    log "Sauvegarde terminée: $tar_file" >&2
    log "Taille de la sauvegarde: $(du -h "$tar_file" | cut -f1)" >&2
    
    # IMPORTANT: Retourner SEULEMENT le chemin du fichier
    echo "$tar_file"
}

# Vérification de l'intégrité de la sauvegarde
verify_backup() {
    local tar_file="$1"
    
    log "Vérification de l'intégrité de la sauvegarde..."
    
    # Vérification de l'existence et de la taille
    if [ ! -f "$tar_file" ]; then
        error "❌ Fichier de sauvegarde introuvable"
    fi
    
    if [ ! -s "$tar_file" ]; then
        error "❌ Fichier de sauvegarde vide"
    fi
    
    # Test de l'archive tar
    if tar -tzf "$tar_file" >/dev/null 2>&1; then
        log "✅ Archive tar valide"
        
        # Vérification du contenu
        local content_count=$(tar -tzf "$tar_file" | wc -l)
        if [ "$content_count" -gt 0 ]; then
            log "✅ Archive contient $content_count fichier(s)"
            
            # Test d'extraction dans un répertoire temporaire
            local temp_dir=$(mktemp -d)
            if tar -xzf "$tar_file" -C "$temp_dir" 2>/dev/null; then
                local extracted_file=$(find "$temp_dir" -name "*.sql" | head -1)
                if [ -n "$extracted_file" ] && [ -s "$extracted_file" ]; then
                    log "✅ Extraction réussie, fichier SQL valide"
                    rm -rf "$temp_dir"
                    return 0
                else
                    warn "⚠️ Fichier SQL extrait semble vide ou invalide"
                fi
            else
                warn "⚠️ Problème lors de l'extraction de test"
            fi
            rm -rf "$temp_dir"
        else
            error "❌ Archive vide"
        fi
    else
        error "❌ Archive tar corrompue ou illisible"
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
    echo "Nombre total: $(find "$BACKUP_DIR" -name "*.tar.gz" -type f 2>/dev/null | wc -l)"
    echo "Espace utilisé: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "N/A")"
    echo "----------------------------------------"
    
    log "📝 Dernières sauvegardes:"
    find "$BACKUP_DIR" -name "*.tar.gz" -type f -printf '%TY-%Tm-%Td %TH:%TM - %f - %s bytes\n' 2>/dev/null | \
    sort -r | head -5 | while read -r line; do
        echo "  $line"
    done || echo "  Aucune sauvegarde trouvée"
}

# Test de restauration (optionnel)
test_restore() {
    local tar_file="$1"
    local test_db="${DB_NAME}_test_restore"
    
    log "🧪 Test de restauration (optionnel)..."
    
    # Extraction du dump
    local temp_dir=$(mktemp -d)
    if tar -xzf "$tar_file" -C "$temp_dir" 2>/dev/null; then
        local sql_file=$(find "$temp_dir" -name "*.sql" | head -1)
        
        if [ -n "$sql_file" ] && [ -s "$sql_file" ]; then
            log "Test de restauration sur une base temporaire..."
            
            # Création d'une base de test
            docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
                createdb -h localhost -U "$DB_USER" "$test_db" 2>/dev/null || true
            
            # Test de restauration
            if docker exec -i -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
                psql -h localhost -U "$DB_USER" -d "$test_db" < "$sql_file" >/dev/null 2>&1; then
                log "✅ Test de restauration réussi"
            else
                warn "⚠️ Test de restauration échoué (cela peut être normal selon la structure de la DB)"
            fi
            
            # Nettoyage de la base de test
            docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
                dropdb -h localhost -U "$DB_USER" "$test_db" 2>/dev/null || true
        else
            warn "⚠️ Fichier SQL introuvable ou vide après extraction"
        fi
    else
        warn "⚠️ Échec de l'extraction de l'archive"
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
    log "📋 Nom de sauvegarde généré: $backup_name"
    
    # Appel de la fonction de sauvegarde avec capture propre du résultat
    local backup_file
    backup_file=$(backup_database "$backup_name")
    local backup_result=$?
    
    if [ $backup_result -eq 0 ] && [ -n "$backup_file" ] && [ -f "$backup_file" ]; then
        log "📁 Fichier créé avec succès: $backup_file"
        
        # Vérification de l'intégrité
        verify_backup "$backup_file"
        
        log "✅ Sauvegarde terminée avec succès!"
        log "📁 Fichier de sauvegarde: $backup_file"
        
        # Affichage du chemin pour faciliter la copie
        echo ""
        echo "Pour restaurer cette sauvegarde:"
        echo "tar -xzf $backup_file"
        echo "docker exec -i -e PGPASSWORD=\"$DB_PASSWORD\" $CONTAINER_NAME psql -h localhost -U $DB_USER -d $DB_NAME < nom_du_fichier.sql"
    else
        error "❌ La sauvegarde a échoué (code: $backup_result, fichier: $backup_file)"
    fi
    
    cleanup_old_backups
    show_backup_stats
}

# Fonction de diagnostic pour débugger les problèmes
debug_backup() {
    log "🔍 Mode diagnostic activé"
    
    echo "=== INFORMATIONS SYSTÈME ==="
    echo "Containers Docker actifs:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    
    echo "=== TEST DE CONNEXION DATABASE ==="
    for container in "postgres_prod" "postgres"; do
        if docker ps --format "{{.Names}}" | grep -q "^$container$"; then
            echo "Test du container: $container"
            docker exec "$container" pg_isready -U "$DB_USER" -d "$DB_NAME" 2>&1 || echo "  ❌ Échec de connexion"
            echo ""
        fi
    done
    
    echo "=== ESPACE DISQUE ==="
    df -h "$BACKUP_DIR" 2>/dev/null || echo "Répertoire de sauvegarde inexistant"
    echo ""
    
    echo "=== PERMISSIONS ==="
    ls -la "$BACKUP_DIR" 2>/dev/null || echo "Impossible de lister le répertoire de sauvegarde"
}

# Gestion des arguments
case "${1:-}" in
    -h|--help)
        echo "Usage: $0 [nom_sauvegarde_optionnel]"
        echo ""
        echo "Options:"
        echo "  -h, --help    Affiche cette aide"
        echo "  -s, --stats   Affiche uniquement les statistiques"
        echo "  -d, --debug   Mode diagnostic"
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
    -d|--debug)
        debug_backup
        exit 0
        ;;
    *)
        main "$1"
        ;;
esac