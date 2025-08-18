#!/bin/bash

# Solution de contournement - Build frontend avec Docker
# Usage: ./docker-build-workaround.sh

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

echo "🐳 CONTOURNEMENT DOCKER POUR LE BUILD FRONTEND"
echo "═══════════════════════════════════════════════"

cd "$APP_DIR" || error "Impossible d'accéder à $APP_DIR"

# Vérifier que Docker est disponible
if ! command -v docker &> /dev/null; then
    error "Docker n'est pas installé"
fi

log "🔧 Création d'un Dockerfile spécial pour le build..."

# Créer un Dockerfile temporaire pour le build uniquement
cat > Dockerfile.frontend-build << 'EOF'
# Dockerfile temporaire pour build frontend
FROM node:18-alpine

WORKDIR /app

# Copier package.json et package-lock.json
COPY frontend/package*.json ./

# Installer les dépendances
RUN npm ci --only=production=false

# Copier le code source
COPY frontend/ ./

# Build
RUN npm run build

# Point de sortie pour copier les fichiers
CMD ["sh", "-c", "cp -r dist/* /output/ 2>/dev/null || cp -r build/* /output/ 2>/dev/null || echo 'Build directory not found'"]
EOF

log "🏗️ Build du frontend avec Docker..."

# Supprimer l'ancien dist/build s'il existe
rm -rf "$FRONTEND_DIR/dist" "$FRONTEND_DIR/build"

# Créer le répertoire de sortie
mkdir -p "$FRONTEND_DIR/dist"

# Build avec Docker
if docker build -f Dockerfile.frontend-build -t ajtpro-frontend-build .; then
    info "✅ Image Docker créée avec succès"
    
    log "📦 Extraction des fichiers buildés..."
    if docker run --rm -v "$FRONTEND_DIR/dist:/output" ajtpro-frontend-build; then
        info "✅ Fichiers extraits avec succès"
        
        # Vérifier que les fichiers existent
        if [ "$(ls -A "$FRONTEND_DIR/dist")" ]; then
            log "📊 Contenu du build:"
            ls -la "$FRONTEND_DIR/dist/"
            
            build_size=$(du -sh "$FRONTEND_DIR/dist" | cut -f1)
            info "✅ Build frontend réussi avec Docker ! Taille: $build_size"
            
            # Nettoyer l'image temporaire
            docker rmi ajtpro-frontend-build || true
            rm -f Dockerfile.frontend-build
            
            echo ""
            log "🎉 Contournement réussi !"
            echo ""
            echo "🚀 Vous pouvez maintenant déployer:"
            echo "   ./deploy.sh install_prod"
            echo ""
            echo "🐳 Ou modifier docker-compose.yml pour build automatiquement:"
            echo "   Le frontend sera buildé à chaque déploiement"
            
        else
            error "❌ Aucun fichier extrait du build Docker"
        fi
    else
        error "❌ Échec de l'extraction des fichiers"
    fi
else
    error "❌ Échec du build Docker"
fi

# Nettoyer en cas d'erreur
rm -f Dockerfile.frontend-build