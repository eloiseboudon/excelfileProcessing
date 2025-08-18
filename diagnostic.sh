#!/bin/bash

# Script de diagnostic AJT Pro
# Usage: ./diagnostic.sh

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
}

info() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')] INFO: $1${NC}"
}

echo "🔍 DIAGNOSTIC AJT PRO"
echo "═══════════════════════════════════════════════"

# 1. Vérification de la structure des répertoires
log "📁 Vérification de la structure des répertoires..."
cd /home/ubuntu

if [ -d "ajtpro" ]; then
    info "✅ Répertoire ajtpro existe"
    
    cd ajtpro
    echo "📋 Contenu du répertoire ajtpro:"
    ls -la
    
    echo ""
    echo "📋 Structure des sous-répertoires:"
    find . -maxdepth 2 -type d | head -10
    
else
    error "❌ Répertoire ajtpro n'existe pas"
    echo "📋 Contenu de /home/ubuntu:"
    ls -la
fi

echo ""
echo "═══════════════════════════════════════════════"

# 2. Vérification Git
log "🔍 Vérification Git..."
cd /home/ubuntu/ajtpro 2>/dev/null || { error "Impossible d'accéder au répertoire ajtpro"; exit 1; }

if [ -d ".git" ]; then
    info "✅ Répertoire .git trouvé"
    
    echo "📋 Statut Git:"
    git status || warn "Erreur git status"
    
    echo ""
    echo "📋 Remote Git:"
    git remote -v || warn "Aucun remote configuré"
    
    echo ""
    echo "📋 Branche actuelle:"
    git branch || warn "Erreur git branch"
    
else
    error "❌ Pas de répertoire .git - Ce n'est pas un repository Git"
    
    echo ""
    echo "🔧 SOLUTION PROPOSÉE:"
    echo "1. Cloner le repository:"
    echo "   cd /home/ubuntu"
    echo "   rm -rf ajtpro  # Si nécessaire"
    echo "   git clone https://github.com/eloiseboudon/excelfileProcessing.git ajtpro"
    echo ""
    echo "2. Ou initialiser Git dans le répertoire existant:"
    echo "   cd /home/ubuntu/ajtpro"
    echo "   git init"
    echo "   git remote add origin https://github.com/eloiseboudon/excelfileProcessing.git"
    echo "   git fetch origin"
    echo "   git checkout -b install_prod origin/install_prod"
fi

echo ""
echo "═══════════════════════════════════════════════"

# 3. Vérification Docker
log "🐳 Vérification Docker..."

echo "📋 Containers en cours:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "📋 Images Docker:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

echo ""
echo "📋 Réseaux Docker:"
docker network ls | grep ajt || warn "Réseau ajtpro_default non trouvé"

echo ""
echo "═══════════════════════════════════════════════"

# 4. Vérification de la base de données
log "🗄️ Vérification de la base de données..."

if docker ps --format "{{.Names}}" | grep -q "postgres"; then
    info "✅ Container PostgreSQL en cours d'exécution"
    
    echo "📋 Test de connexion:"
    if docker exec postgres pg_isready -U ajt_user -d ajt_db 2>/dev/null; then
        info "✅ Base de données accessible"
        
        echo "📋 Taille de la base:"
        docker exec -e PGPASSWORD="ajt_password" postgres \
            psql -h localhost -U ajt_user -d ajt_db -c \
            "SELECT pg_size_pretty(pg_database_size('ajt_db'));" 2>/dev/null || warn "Erreur taille DB"
    else
        warn "❌ Base de données inaccessible"
    fi
else
    warn "❌ Container PostgreSQL non trouvé"
fi

echo ""
echo "═══════════════════════════════════════════════"

# 5. Vérification des sauvegardes
log "💾 Vérification des sauvegardes..."

BACKUP_DB_DIR="/home/ubuntu/backups/database"
BACKUP_DEPLOY_DIR="/home/ubuntu/backups/deployments"

echo "📋 Répertoires de sauvegarde:"
for dir in "$BACKUP_DB_DIR" "$BACKUP_DEPLOY_DIR"; do
    if [ -d "$dir" ]; then
        info "✅ $dir existe"
        echo "   Contenu (5 derniers):"
        ls -lt "$dir" 2>/dev/null | head -6 || echo "   Vide"
    else
        warn "❌ $dir n'existe pas"
    fi
done

# Test de la dernière sauvegarde DB
if [ -d "$BACKUP_DB_DIR" ]; then
    latest_backup=$(find "$BACKUP_DB_DIR" -name "*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    if [ -n "$latest_backup" ]; then
        echo ""
        echo "📋 Test de la dernière sauvegarde DB:"
        echo "   Fichier: $(basename "$latest_backup")"
        echo "   Taille: $(du -h "$latest_backup" 2>/dev/null | cut -f1 || echo "N/A")"
        
        if tar -tzf "$latest_backup" >/dev/null 2>&1; then
            info "✅ Sauvegarde valide"
        else
            error "❌ Sauvegarde corrompue: $latest_backup"
        fi
    else
        warn "Aucune sauvegarde DB trouvée"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════"

# 6. Vérification des scripts
log "📜 Vérification des scripts..."

cd /home/ubuntu/ajtpro 2>/dev/null || exit 1

scripts=("deploy.sh" "quick-deploy.sh" "save_db.sh")
for script in "${scripts[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            info "✅ $script existe et est exécutable"
        else
            warn "⚠️  $script existe mais n'est pas exécutable"
            echo "   Solution: chmod +x $script"
        fi
    else
        warn "❌ $script manquant"
    fi
done

echo ""
echo "═══════════════════════════════════════════════"

# 7. Vérification des ports
log "🌐 Vérification des ports..."

ports=(3000 8000 5432)
for port in "${ports[@]}"; do
    if netstat -ln 2>/dev/null | grep -q ":$port "; then
        info "✅ Port $port en écoute"
    else
        warn "❌ Port $port non utilisé"
    fi
done

echo ""
echo "═══════════════════════════════════════════════"

# 8. Résumé et recommandations
log "📋 RÉSUMÉ ET RECOMMANDATIONS"

echo ""
echo "🔧 ACTIONS RECOMMANDÉES:"

# Problème Git
if [ ! -d "/home/ubuntu/ajtpro/.git" ]; then
    echo "1. 🔴 URGENT - Corriger le problème Git:"
    echo "   ./fix-git.sh  # (script à créer)"
fi

# Problème sauvegarde
if [ -d "$BACKUP_DB_DIR" ]; then
    latest_backup=$(find "$BACKUP_DB_DIR" -name "*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    if [ -n "$latest_backup" ] && ! tar -tzf "$latest_backup" >/dev/null 2>&1; then
        echo "2. 🔴 URGENT - Réparer les sauvegardes DB:"
        echo "   ./fix-backup.sh  # (script à créer)"
    fi
fi

# Recommandations générales
echo "3. 🟡 Vérifications de routine:"
echo "   - docker-compose ps"
echo "   - docker-compose logs"
echo "   - ./save_db.sh --stats"

echo ""
echo "🎯 Une fois les problèmes corrigés, relancer:"
echo "   ./deploy.sh install_prod"

echo ""
echo "═══════════════════════════════════════════════"