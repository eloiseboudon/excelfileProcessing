#!/bin/bash

# Script de déploiement rapide
# Usage: ./quick-deploy.sh

set -e

APP_DIR="/opt/votre-app"
BRANCH="main"

echo "🚀 Déploiement rapide en cours..."

# Aller dans le répertoire de l'app
cd "$APP_DIR"

# Mise à jour du code
echo "📥 Récupération des dernières modifications..."
git pull origin "$BRANCH"

# Build du frontend
echo "🔨 Build du frontend..."
npm ci
npm run build

# Redémarrage des containers
echo "🔄 Redémarrage des containers..."
docker-compose down
docker-compose up -d --build

# Attendre un peu
sleep 10

# Test de santé
echo "🏥 Test de santé..."
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Déploiement réussi !"
else
    echo "❌ Erreur lors du déploiement"
    exit 1
fi

echo "🎉 Application déployée et accessible !"