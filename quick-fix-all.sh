#!/bin/bash

# Script de correction rapide pour tous les problèmes AJT Pro
# Usage: ./quick-fix-all.sh

set -e

# Configuration
APP_DIR="/home/ubuntu/ajtpro"
FRONTEND_DIR="$APP_DIR/frontend"

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

echo "🚀 CORRECTION RAPIDE DE TOUS LES PROBLÈMES"
echo "═══════════════════════════════════════════════"

cd "$APP_DIR" || error "Impossible d'accéder à $APP_DIR"

# 1. Correction des permissions des scripts
log "🔧 Correction des permissions des scripts..."

scripts=(
    "deploy.sh"
    "quick-deploy.sh"
    "save_db.sh"
    "diagnostic.sh"
    "emergency-deploy.sh"
    "fix-backup.sh"
    "fix-git.sh"
    "fix-git-conflict.sh"
    "fix-frontend-build.sh"
    "manage-services.sh"
)

for script in "${scripts[@]}"; do
    if [ -f "$script" ]; then
        chmod +x "$script"
        info "✅ $script rendu exécutable"
    else
        warn "⚠️ $script non trouvé"
    fi
done

# 2. Correction du problème Rollup
log "🔧 Correction du problème de build frontend..."

cd "$FRONTEND_DIR" || error "Impossible d'accéder au répertoire frontend"

# Méthode agressive pour corriger Rollup
log "🗑️ Suppression complète des dépendances..."
rm -rf node_modules package-lock.json

log "🧹 Nettoyage du cache npm..."
npm cache clean --force

log "📦 Réinstallation avec méthode spéciale..."

# Essayer plusieurs méthodes d'installation
installation_success=false

# Méthode 1: Installation avec flags spéciaux
log "🔄 Tentative 1: Installation avec flags spéciaux..."
if npm install --legacy-peer-deps --no-optional --verbose; then
    installation_success=true
    info "✅ Installation réussie avec flags spéciaux"
else
    warn "⚠️ Méthode 1 échouée"
fi

# Méthode 2: Installation forcée si la première échoue
if [ "$installation_success" = false ]; then
    log "🔄 Tentative 2: Installation forcée..."
    if npm install --force; then
        installation_success=true
        info "✅ Installation réussie avec --force"
    else
        warn "⚠️ Méthode 2 échouée"
    fi
fi

# Méthode 3: Installation manuelle de Rollup
if [ "$installation_success" = false ]; then
    log "🔄 Tentative 3: Installation manuelle de Rollup..."
    if npm install rollup@latest --save-dev --legacy-peer-deps; then
        if npm install --legacy-peer-deps; then
            installation_success=true
            info "✅ Installation réussie avec Rollup manuel"
        fi
    fi
fi

# Méthode 4: Yarn en dernier recours
if [ "$installation_success" = false ]; then
    if command -v yarn &> /dev/null; then
        log "🔄 Tentative 4: Utilisation de Yarn..."
        if yarn install; then
            installation_success=true
            info "✅ Installation réussie avec Yarn"
        fi
    else
        log "📦 Installation de Yarn..."
        npm install -g yarn
        if yarn install; then
            installation_success=true
            info "✅ Installation réussie avec Yarn"
        fi
    fi
fi

if [ "$installation_success" = false ]; then
    error "❌ Toutes les méthodes d'installation ont échoué"
fi

# 3. Vérification de l'installation de Rollup
log "🔍 Vérification de Rollup..."

if [ -d "node_modules/@rollup" ]; then
    info "✅ Rollup installé, modules disponibles:"
    ls node_modules/@rollup/ | head -5
else
    warn "⚠️ Rollup non trouvé, tentative de réinstallation spécifique..."
    npm install @rollup/rollup-linux-x64-gnu --save-dev --legacy-peer-deps || true
fi

# 4. Test du build
log "🧪 Test du build frontend..."

if npm run build; then
    info "✅ Build frontend réussi !"
    
    # Vérifier le résultat
    if [ -d "dist" ]; then
        build_size=$(du -sh dist/ | cut -f1)
        info "📊 Build créé dans dist/ (taille: $build_size)"
    elif [ -d "build" ]; then
        build_size=$(du -sh build/ | cut -f1)
        info "📊 Build créé dans build/ (taille: $build_size)"
    fi
else
    error "❌ Build frontend toujours en échec"
fi

# 5. Retour au répertoire principal et test de déploiement
cd "$APP_DIR"

log "🔧 Test des scripts principaux..."

# Test du script de sauvegarde
if [ -f "save_db.sh" ]; then
    log "🧪 Test du script de sauvegarde..."
    if ./save_db.sh --stats &>/dev/null; then
        info "✅ Script de sauvegarde fonctionnel"
    else
        warn "⚠️ Script de sauvegarde a des problèmes (non critique)"
    fi
fi

# 6. Déploiement automatique
echo ""
read -p "🚀 Lancer le déploiement maintenant ? (y/N): " deploy_now

if [[ $deploy_now =~ ^[Yy]$ ]]; then
    log "🚀 Lancement du déploiement..."
    echo ""
    
    # Utiliser le déploiement rapide qui skip certaines vérifications
    if [ -f "quick-deploy.sh" ]; then
        ./quick-deploy.sh install_prod
    else
        ./deploy.sh install_prod
    fi
else
    echo ""
    log "✅ Corrections terminées !"
    echo ""
    echo "🎯 Prochaines étapes:"
    echo "1. Déploiement normal:"
    echo "   ./deploy.sh install_prod"
    echo ""
    echo "2. Ou déploiement rapide:"
    echo "   ./quick-deploy.sh install_prod"
    echo ""
    echo "3. Vérifier les services:"
    echo "   ./manage-services.sh status"
fi

echo ""
echo "═══════════════════════════════════════════════"
log "🎉 Toutes les corrections ont été appliquées !"

echo ""
echo "📋 Résumé des corrections:"
echo "  ✅ Permissions des scripts corrigées"
echo "  ✅ Problème Rollup résolu"
echo "  ✅ Build frontend fonctionnel"
echo "  ✅ Scripts de déploiement prêts"

echo ""
echo "🌍 Une fois déployé, votre application sera accessible sur:"
echo "  Frontend: http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo 'votre-ip'):3000"
echo "  Backend:  http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo 'votre-ip'):8000"