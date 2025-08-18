#!/bin/bash

# Script de résolution des conflits Git AJT Pro
# Usage: ./fix-git-conflict.sh

set -e

# Configuration
APP_DIR="/home/ubuntu/ajtpro"
BRANCH="install_prod"
BACKUP_SUFFIX="backup_$(date +%Y%m%d_%H%M%S)"

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

echo "🔧 RÉSOLUTION DES CONFLITS GIT"
echo "═══════════════════════════════════════════════"

cd "$APP_DIR" || error "Impossible d'accéder à $APP_DIR"

# Vérification de l'état Git
log "🔍 Analyse de la situation Git..."

if [ ! -d ".git" ]; then
    error "❌ Pas de répertoire .git trouvé"
fi

echo "📋 Statut Git actuel:"
git status --porcelain

echo ""
echo "📋 Branche actuelle:"
git branch 2>/dev/null || echo "Aucune branche"

echo ""
echo "📋 Fichiers non-trackés qui causent le conflit:"
git ls-files --others --exclude-standard | head -20

# Proposer les solutions
echo ""
echo "🤔 Solutions disponibles pour résoudre le conflit:"
echo ""
echo "1. 💾 SAUVEGARDER et REMPLACER (Recommandé)"
echo "   - Sauvegarde vos fichiers locaux"
echo "   - Force le checkout vers la branche distante"
echo "   - Vous pouvez comparer/récupérer vos modifications après"
echo ""
echo "2. 📝 COMMITTER et MERGER"
echo "   - Ajoute vos fichiers locaux au repository"
echo "   - Les commit sur la branche actuelle"
echo "   - Merge avec la branche distante"
echo ""
echo "3. 🗑️  SUPPRIMER et CHECKOUT"
echo "   - Supprime tous les fichiers en conflit"
echo "   - Checkout propre vers la branche distante"
echo "   - ⚠️ PERTE DÉFINITIVE de vos modifications locales"
echo ""
echo "4. 📊 COMPARAISON DÉTAILLÉE"
echo "   - Compare vos fichiers avec ceux du repository"
echo "   - Vous aide à décider quoi garder"
echo ""

read -p "Choisissez une option (1-4): " choice

case $choice in
    1)
        log "💾 SAUVEGARDE ET REMPLACEMENT"
        
        # Créer le répertoire de sauvegarde
        backup_dir="/home/ubuntu/local_files_$BACKUP_SUFFIX"
        mkdir -p "$backup_dir"
        
        log "📁 Sauvegarde des fichiers locaux vers: $backup_dir"
        
        # Lister et sauvegarder les fichiers non-trackés
        git ls-files --others --exclude-standard > "$backup_dir/untracked_files.txt"
        
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                # Créer le répertoire parent dans la sauvegarde
                backup_file_dir="$backup_dir/$(dirname "$file")"
                mkdir -p "$backup_file_dir"
                
                # Copier le fichier
                cp "$file" "$backup_dir/$file"
                info "📄 Sauvegardé: $file"
            fi
        done < "$backup_dir/untracked_files.txt"
        
        # Supprimer les fichiers en conflit
        log "🗑️ Suppression des fichiers en conflit..."
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                rm -f "$file"
            fi
        done < "$backup_dir/untracked_files.txt"
        
        # Checkout de la branche
        log "🌿 Checkout vers la branche $BRANCH..."
        git checkout "$BRANCH"
        
        info "✅ Checkout réussi !"
        echo ""
        echo "📁 Vos fichiers locaux sont sauvegardés dans: $backup_dir"
        echo "📋 Liste des fichiers sauvegardés: $backup_dir/untracked_files.txt"
        echo ""
        echo "🔍 Pour comparer vos modifications:"
        echo "   diff -r $backup_dir/backend backend/ || true"
        echo "   diff -r $backup_dir/frontend frontend/ || true"
        ;;
        
    2)
        log "📝 COMMIT ET MERGE"
        
        # Ajouter tous les fichiers
        log "➕ Ajout de tous les fichiers locaux..."
        git add .
        
        # Commit
        commit_msg="Local files before merge with $BRANCH - $(date)"
        log "💾 Commit des modifications locales..."
        git commit -m "$commit_msg"
        
        # Checkout de la branche distante
        log "🌿 Checkout vers $BRANCH..."
        git checkout "$BRANCH"
        
        # Merge de la branche précédente
        prev_branch=$(git branch --show-current)
        log "🔀 Merge des modifications locales..."
        git merge "$prev_branch" || {
            warn "⚠️ Conflits de merge détectés !"
            echo ""
            echo "🔧 Résoudre les conflits manuellement:"
            echo "   git status                 # Voir les conflits"
            echo "   # Éditer les fichiers en conflit"
            echo "   git add <fichiers_résolus>"
            echo "   git commit"
            exit 1
        }
        
        info "✅ Merge réussi !"
        ;;
        
    3)
        log "🗑️ SUPPRESSION ET CHECKOUT"
        
        warn "⚠️ ATTENTION: Cette action supprimera définitivement vos fichiers locaux !"
        read -p "Êtes-vous absolument sûr? Tapez 'SUPPRIMER' pour confirmer: " confirm
        
        if [ "$confirm" = "SUPPRIMER" ]; then
            log "🗑️ Suppression des fichiers en conflit..."
            
            # Supprimer les fichiers non-trackés
            git ls-files --others --exclude-standard | while IFS= read -r file; do
                if [ -f "$file" ]; then
                    rm -f "$file"
                    echo "   🗑️ Supprimé: $file"
                fi
            done
            
            # Checkout
            log "🌿 Checkout vers $BRANCH..."
            git checkout "$BRANCH"
            
            info "✅ Checkout réussi !"
        else
            warn "Opération annulée"
            exit 0
        fi
        ;;
        
    4)
        log "📊 COMPARAISON DÉTAILLÉE"
        
        # Créer un répertoire temporaire pour la branche distante
        temp_dir="/tmp/ajtpro_remote_$BACKUP_SUFFIX"
        mkdir -p "$temp_dir"
        
        log "📥 Récupération des fichiers de la branche distante..."
        git show "origin/$BRANCH:docker-compose.yml" > "$temp_dir/docker-compose.yml" 2>/dev/null || true
        git show "origin/$BRANCH:deploy.sh" > "$temp_dir/deploy.sh" 2>/dev/null || true
        
        echo ""
        echo "🔍 COMPARAISONS IMPORTANTES:"
        echo ""
        
        # Comparer les fichiers clés
        key_files=("docker-compose.yml" "deploy.sh")
        for file in "${key_files[@]}"; do
            if [ -f "$file" ] && [ -f "$temp_dir/$file" ]; then
                echo "📄 Différences dans $file:"
                diff -u "$temp_dir/$file" "$file" || echo "   (Fichiers identiques)"
                echo ""
            fi
        done
        
        # Nettoyer
        rm -rf "$temp_dir"
        
        echo "💡 Après cette analyse, relancez le script pour choisir une action"
        exit 0
        ;;
        
    *)
        error "❌ Option invalide"
        ;;
esac

# Vérification finale
echo ""
log "🔍 Vérification finale..."
echo "📋 Statut Git:"
git status

echo ""
echo "📋 Branche actuelle:"
git branch --show-current

echo ""
echo "📋 Derniers commits:"
git log --oneline -5

echo ""
echo "═══════════════════════════════════════════════"
log "✅ Résolution des conflits Git terminée !"

echo ""
echo "🎯 Prochaines étapes:"
echo "1. Vérifier que vos fichiers sont corrects:"
echo "   ls -la backend/ frontend/"
echo ""
echo "2. Tester le déploiement:"
echo "   ./deploy.sh install_prod"
echo ""

if [ "$choice" = "1" ]; then
    echo "3. Si nécessaire, récupérer des éléments de votre sauvegarde:"
    echo "   diff -r /home/ubuntu/local_files_$BACKUP_SUFFIX/backend backend/"
    echo "   # Puis copier les fichiers nécessaires"
    echo ""
fi

echo "🎉 Vous pouvez maintenant déployer normalement !"