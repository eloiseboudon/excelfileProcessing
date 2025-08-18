#!/bin/bash

# Script de correction Git pour AJT Pro
# Usage: ./fix-git.sh

set -e

# Configuration
REPO_URL="https://github.com/eloiseboudon/excelfileProcessing.git"
APP_DIR="/home/ubuntu/ajtpro"
BRANCH="install_prod"

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

echo "🔧 CORRECTION DU PROBLÈME GIT"
echo "═══════════════════════════════════════════════"

# Vérification de l'état actuel
log "🔍 Analyse de la situation actuelle..."

cd /home/ubuntu

if [ ! -d "ajtpro" ]; then
    error "❌ Répertoire ajtpro n'existe pas"
fi

cd ajtpro

# Vérifier s'il y a du contenu important
has_important_files=false
important_files=("docker-compose.yml" "frontend" "backend" "deploy.sh" "save_db.sh")

for file in "${important_files[@]}"; do
    if [ -e "$file" ]; then
        has_important_files=true
        break
    fi
done

if [ "$has_important_files" = true ]; then
    log "📁 Fichiers importants détectés dans le répertoire"
    echo "📋 Contenu actuel:"
    ls -la
    echo ""
    
    # Sauvegarde des fichiers existants
    log "💾 Sauvegarde des fichiers existants..."
    backup_dir="/home/ubuntu/backup_before_git_fix_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    cp -r * "$backup_dir/" 2>/dev/null || true
    info "✅ Sauvegarde créée dans: $backup_dir"
fi

# Choix de la méthode de correction
echo ""
echo "🤔 Méthodes de correction disponibles:"
echo "1. Réinitialiser Git dans le répertoire existant (recommandé)"
echo "2. Cloner le repository dans un nouveau répertoire"
echo "3. Initialiser un nouveau repository Git"
echo ""

read -p "Choisissez une option (1-3): " choice

case $choice in
    1)
        log "🔄 Réinitialisation Git dans le répertoire existant..."
        
        # Supprimer l'ancien .git s'il existe
        if [ -d ".git" ]; then
            rm -rf .git
        fi
        
        # Initialiser Git
        git init
        git remote add origin "$REPO_URL"
        
        log "📥 Récupération des branches distantes..."
        git fetch origin
        
        # Vérifier si la branche existe
        if git ls-remote --heads origin "$BRANCH" | grep -q "$BRANCH"; then
            log "🌿 Checkout de la branche $BRANCH..."
            git checkout -b "$BRANCH" "origin/$BRANCH"
        else
            warn "⚠️  Branche $BRANCH introuvable, utilisation de main/master"
            if git ls-remote --heads origin main | grep -q main; then
                git checkout -b main origin/main
            elif git ls-remote --heads origin master | grep -q master; then
                git checkout -b master origin/master
            else
                error "❌ Aucune branche principale trouvée"
            fi
        fi
        
        info "✅ Git réinitialisé avec succès"
        ;;
        
    2)
        log "🔄 Clone du repository dans un nouveau répertoire..."
        
        cd /home/ubuntu
        
        # Renommer l'ancien répertoire
        if [ -d "ajtpro" ]; then
            mv ajtpro "ajtpro_old_$(date +%Y%m%d_%H%M%S)"
        fi
        
        # Cloner le repository
        if git ls-remote --heads "$REPO_URL" "$BRANCH" | grep -q "$BRANCH"; then
            git clone -b "$BRANCH" "$REPO_URL" ajtpro
        else
            warn "⚠️  Branche $BRANCH introuvable, clone de la branche principale"
            git clone "$REPO_URL" ajtpro
        fi
        
        cd ajtpro
        info "✅ Repository cloné avec succès"
        ;;
        
    3)
        log "🆕 Initialisation d'un nouveau repository Git..."
        
        git init
        git remote add origin "$REPO_URL"
        
        # Créer un commit initial avec les fichiers existants
        git add .
        git commit -m "Initial commit - existing files"
        
        info "✅ Repository Git initialisé"
        ;;
        
    *)
        error "❌ Option invalide"
        ;;
esac

# Vérification finale
echo ""
log "🔍 Vérification de la configuration Git..."

echo "📋 Statut Git:"
git status

echo ""
echo "📋 Remote configuré:"
git remote -v

echo ""
echo "📋 Branche actuelle:"
git branch

echo ""
echo "📋 Derniers commits:"
git log --oneline -5 2>/dev/null || echo "Aucun commit"

echo ""
echo "═══════════════════════════════════════════════"
log "✅ Correction Git terminée!"

echo ""
echo "🎯 Prochaines étapes:"
echo "1. Vérifier que vos fichiers sont bien présents:"
echo "   ls -la"
echo ""
echo "2. Si vous avez perdu des fichiers, les restaurer depuis la sauvegarde:"
echo "   cp /home/ubuntu/backup_before_git_fix_*/fichier_manquant ."
echo ""
echo "3. Relancer le déploiement:"
echo "   ./deploy.sh install_prod"

echo ""
echo "⚠️  IMPORTANT: Vérifiez que tous vos fichiers importants sont présents!"
echo "Sauvegardes disponibles dans /home/ubuntu/backup_before_git_fix_*"