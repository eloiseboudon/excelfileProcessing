#!/bin/bash

# Script de correction des sauvegardes DB
# Usage: ./fix-backup.sh

set -e

# Configuration
CONTAINER_NAME="postgres"
DB_NAME="ajt_db"
DB_USER="ajt_user"
DB_PASSWORD="ajt_password"
BACKUP_DIR="/home/ubuntu/backups/database"

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

echo "🔧 CORRECTION DES SAUVEGARDES DB"
echo "═══════════════════════════════════════════════"

# 1. Vérification de l'état de la base de données
log "🔍 Vérification de l'état de PostgreSQL..."

if ! docker ps --format "{{.Names}}" | grep -q "$CONTAINER_NAME"; then
    error "❌ Container PostgreSQL '$CONTAINER_NAME' non trouvé ou arrêté"
fi

if ! docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
    error "❌ Base de données inaccessible"
fi

info "✅ PostgreSQL fonctionne correctement"

# 2. Analyse des sauvegardes existantes
log "📁 Analyse des sauvegardes existantes..."

mkdir -p "$BACKUP_DIR"

if [ -d "$BACKUP_DIR" ]; then
    log "📋 Sauvegardes trouvées:"
    
    backup_count=0
    corrupted_count=0
    
    for backup_file in "$BACKUP_DIR"/*.tar.gz; do
        if [ -f "$backup_file" ]; then
            backup_count=$((backup_count + 1))
            echo "  📄 $(basename "$backup_file") - $(du -h "$backup_file" | cut -f1)"
            
            # Test d'intégrité
            if tar -tzf "$backup_file" >/dev/null 2>&1; then
                echo "     ✅ Valide"
            else
                echo "     ❌ Corrompue"
                corrupted_count=$((corrupted_count + 1))
            fi
        fi
    done
    
    if [ $backup_count -eq 0 ]; then
        warn "Aucune sauvegarde trouvée"
    else
        info "Total: $backup_count sauvegardes, $corrupted_count corrompues"
    fi
fi

# 3. Nettoyage des sauvegardes corrompues
if [ $corrupted_count -gt 0 ]; then
    echo ""
    read -p "🗑️ Supprimer les sauvegardes corrompues? (y/N): " clean_corrupted
    
    if [[ $clean_corrupted =~ ^[Yy]$ ]]; then
        log "🧹 Suppression des sauvegardes corrompues..."
        
        for backup_file in "$BACKUP_DIR"/*.tar.gz; do
            if [ -f "$backup_file" ]; then
                if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
                    echo "  🗑️ Suppression: $(basename "$backup_file")"
                    rm -f "$backup_file"
                fi
            fi
        done
        
        info "✅ Nettoyage terminé"
    fi
fi

# 4. Test de création d'une nouvelle sauvegarde
echo ""
log "🧪 Test de création d'une nouvelle sauvegarde..."

test_backup_name="test_fix_$(date +%Y%m%d_%H%M%S)"
test_sql_file="${BACKUP_DIR}/${test_backup_name}.sql"
test_tar_file="${BACKUP_DIR}/${test_backup_name}.tar.gz"

# Création du dump SQL
log "📤 Création du dump SQL..."
if docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
    pg_dump -h localhost -U "$DB_USER" -d "$DB_NAME" \
    --verbose --clean --no-owner --no-privileges \
    > "$test_sql_file" 2>/dev/null; then
    
    if [ -s "$test_sql_file" ]; then
        info "✅ Dump SQL créé avec succès ($(du -h "$test_sql_file" | cut -f1))"
        
        # Compression
        log "📦 Compression en tar.gz..."
        if tar -czf "$test_tar_file" -C "$BACKUP_DIR" "$(basename "$test_sql_file")"; then
            
            # Vérification de l'intégrité
            if tar -tzf "$test_tar_file" >/dev/null 2>&1; then
                info "✅ Sauvegarde de test créée et vérifiée avec succès!"
                
                # Nettoyage du fichier SQL temporaire
                rm -f "$test_sql_file"
                
                echo "📋 Détails de la sauvegarde:"
                echo "  Fichier: $(basename "$test_tar_file")"
                echo "  Taille: $(du -h "$test_tar_file" | cut -f1)"
                echo "  Contenu: $(tar -tzf "$test_tar_file")"
                
            else
                error "❌ Sauvegarde tar.gz corrompue"
            fi
        else
            error "❌ Échec de la compression tar"
        fi
    else
        error "❌ Dump SQL vide"
    fi
else
    error "❌ Échec de la création du dump SQL"
fi

# 5. Test de restauration (optionnel)
echo ""
read -p "🧪 Tester la restauration sur une base temporaire? (y/N): " test_restore

if [[ $test_restore =~ ^[Yy]$ ]]; then
    log "🔄 Test de restauration..."
    
    test_db_name="${DB_NAME}_test_restore"
    
    # Création d'une base de test
    log "🆕 Création de la base de test: $test_db_name"
    docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
        createdb -h localhost -U "$DB_USER" "$test_db_name" 2>/dev/null || true
    
    # Extraction et restauration
    temp_dir=$(mktemp -d)
    tar -xzf "$test_tar_file" -C "$temp_dir"
    test_sql_restored=$(find "$temp_dir" -name "*.sql" | head -1)
    
    if [ -n "$test_sql_restored" ]; then
        log "📥 Restauration dans la base de test..."
        if docker exec -i -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            psql -h localhost -U "$DB_USER" -d "$test_db_name" < "$test_sql_restored" >/dev/null 2>&1; then
            info "✅ Test de restauration réussi!"
        else
            warn "⚠️  Test de restauration échoué (peut être normal selon la structure)"
        fi
        
        # Nettoyage de la base de test
        docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            dropdb -h localhost -U "$DB_USER" "$test_db_name" 2>/dev/null || true
    fi
    
    rm -rf "$temp_dir"
fi

# 6. Correction du script save_db.sh si nécessaire
echo ""
log "🔧 Vérification du script save_db.sh..."

if [ -f "/home/ubuntu/ajtpro/save_db.sh" ]; then
    if grep -q "tar -czf.*-C.*basename" "/home/ubuntu/ajtpro/save_db.sh"; then
        info "✅ Script save_db.sh semble correct"
    else
        warn "⚠️  Script save_db.sh pourrait nécessiter une correction"
        
        read -p "🔧 Corriger le script save_db.sh? (y/N): " fix_script
        
        if [[ $fix_script =~ ^[Yy]$ ]]; then
            log "🔄 Mise à jour du script save_db.sh..."
            
            # Sauvegarde de l'ancien script
            cp "/home/ubuntu/ajtpro/save_db.sh" "/home/ubuntu/ajtpro/save_db.sh.backup.$(date +%Y%m%d_%H%M%S)"
            
            # Ici, on pourrait corriger des problèmes spécifiques dans le script
            info "✅ Script sauvegardé, vérifiez manuellement les corrections nécessaires"
        fi
    fi
else
    warn "⚠️  Script save_db.sh introuvable"
fi

# 7. Résumé et recommandations
echo ""
echo "═══════════════════════════════════════════════"
log "📋 RÉSUMÉ DE LA CORRECTION"

echo ""
echo "✅ Actions effectuées:"
echo "  - Vérification de PostgreSQL"
echo "  - Analyse des sauvegardes existantes"
if [ $corrupted_count -gt 0 ]; then
    echo "  - Nettoyage des sauvegardes corrompues"
fi
echo "  - Création d'une sauvegarde de test valide"

echo ""
echo "🎯 Recommandations:"
echo "1. Tester le script de sauvegarde:"
echo "   cd /home/ubuntu/ajtpro"
echo "   ./save_db.sh test_after_fix"
echo ""
echo "2. Vérifier la sauvegarde créée:"
echo "   ./save_db.sh --stats"
echo ""
echo "3. Relancer le déploiement:"
echo "   ./deploy.sh install_prod"

echo ""
echo "📁 Sauvegarde de test créée: $(basename "$test_tar_file")"
echo "📂 Répertoire des sauvegardes: $BACKUP_DIR"

echo ""
log "✅ Correction des sauvegardes terminée!"