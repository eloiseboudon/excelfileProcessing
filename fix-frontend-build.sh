#!/bin/bash

# Script de correction du build frontend
# Usage: ./fix-frontend-build.sh

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

echo "🔧 CORRECTION DU BUILD FRONTEND"
echo "═══════════════════════════════════════════════"

# Vérifier que le répertoire frontend existe
if [ ! -d "$FRONTEND_DIR" ]; then
    error "❌ Répertoire frontend non trouvé: $FRONTEND_DIR"
fi

cd "$FRONTEND_DIR"

# Vérifier package.json
if [ ! -f "package.json" ]; then
    error "❌ package.json non trouvé dans le répertoire frontend"
fi

log "📋 Diagnostic du problème..."

# Afficher les informations actuelles
echo "📦 Version de Node.js: $(node --version)"
echo "📦 Version de npm: $(npm --version)"
echo ""

# Vérifier l'espace disque
echo "💾 Espace disque disponible:"
df -h . | tail -1
echo ""

# Solution 1: Nettoyage complet et réinstallation
log "🧹 Solution 1: Nettoyage complet des dépendances..."

echo "🗑️ Suppression de node_modules et package-lock.json..."

# Supprimer node_modules
if [ -d "node_modules" ]; then
    rm -rf node_modules
    info "✅ node_modules supprimé"
else
    info "📁 node_modules n'existait pas"
fi

# Supprimer package-lock.json
if [ -f "package-lock.json" ]; then
    rm -f package-lock.json
    info "✅ package-lock.json supprimé"
else
    info "📄 package-lock.json n'existait pas"
fi

# Nettoyer le cache npm
log "🧹 Nettoyage du cache npm..."
npm cache clean --force

# Réinstaller les dépendances
log "📦 Réinstallation des dépendances..."
echo "⏳ Cela peut prendre quelques minutes..."

# Installation avec flags pour éviter les problèmes
if npm install --no-optional --legacy-peer-deps; then
    info "✅ Installation réussie avec --no-optional --legacy-peer-deps"
elif npm install --legacy-peer-deps; then
    info "✅ Installation réussie avec --legacy-peer-deps"
elif npm install --force; then
    info "✅ Installation réussie avec --force"
else
    warn "⚠️ Installation standard échouée, tentative avec d'autres méthodes..."
    
    # Solution alternative: utiliser yarn si disponible
    if command -v yarn &> /dev/null; then
        log "📦 Tentative avec Yarn..."
        yarn install
        info "✅ Installation réussie avec Yarn"
    else
        error "❌ Toutes les tentatives d'installation ont échoué"
    fi
fi

# Vérifier que rollup est bien installé
log "🔍 Vérification de l'installation de Rollup..."

if [ -d "node_modules/@rollup" ]; then
    echo "📋 Modules Rollup installés:"
    ls -la node_modules/@rollup/ | head -10
    info "✅ Rollup semble correctement installé"
else
    warn "⚠️ Modules Rollup non trouvés, tentative de réinstallation..."
    npm install rollup @rollup/plugin-node-resolve @rollup/plugin-commonjs --save-dev
fi

# Test du build
echo ""
log "🧪 Test du build..."

if npm run build; then
    info "✅ Build réussi !"
    
    # Vérifier que les fichiers de build existent
    if [ -d "dist" ]; then
        echo "📋 Contenu du répertoire dist:"
        ls -la dist/ | head -10
        echo "📊 Taille du build: $(du -sh dist/ | cut -f1)"
    elif [ -d "build" ]; then
        echo "📋 Contenu du répertoire build:"
        ls -la build/ | head -10
        echo "📊 Taille du build: $(du -sh build/ | cut -f1)"
    else
        warn "⚠️ Aucun répertoire dist/ ou build/ trouvé après le build"
    fi
    
else
    error "❌ Le build échoue encore, diagnostic approfondi nécessaire"
fi

echo ""
echo "═══════════════════════════════════════════════"
log "✅ Correction du build frontend terminée !"

echo ""
echo "🎯 Le frontend est maintenant prêt pour le déploiement"
echo ""
echo "📋 Prochaines étapes:"
echo "1. Retourner au répertoire principal:"
echo "   cd $APP_DIR"
echo ""
echo "2. Relancer le déploiement:"
echo "   ./deploy.sh install_prod"
echo ""
echo "3. Ou utiliser le déploiement rapide:"
echo "   ./quick-deploy.sh"

# Retourner au répertoire principal
cd "$APP_DIR"