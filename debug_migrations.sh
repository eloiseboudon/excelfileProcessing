#!/bin/bash

# Script de diagnostic pour les migrations Alembic
# Usage: ./debug_migrations.sh

set -e

# Configuration
DOCKER_COMPOSE_FILE="docker-compose.yml"
DOCKER_COMPOSE_PROD_FILE="docker-compose.prod.yml"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Détection de docker-compose
DOCKER_COMPOSE_CMD="docker compose"


# Sélection du fichier docker-compose
COMPOSE_FILE="$DOCKER_COMPOSE_FILE"
if [ -f "$DOCKER_COMPOSE_PROD_FILE" ]; then
    read -p "Utiliser le fichier de production ? (y/N): " use_prod
    if [[ $use_prod =~ ^[Yy]$ ]]; then
        COMPOSE_FILE="$DOCKER_COMPOSE_PROD_FILE"
    fi
fi

log "🔍 Diagnostic des migrations Alembic"
echo "════════════════════════════════════════════════════════════════"

# 1. État des containers
log "📊 État des containers:"
$DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps
echo ""

# 2. Vérification de la base de données
log "🗄️ Test de connexion à la base de données:"
if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres pg_isready -h localhost -p 5432; then
    info "✅ PostgreSQL accessible"
else
    error "❌ PostgreSQL inaccessible"
fi
echo ""

# 3. Variables d'environnement
log "🌍 Variables d'environnement du backend:"
echo "────────────────────────────────────────────────────────────────"
$DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend env | grep -E "(DATABASE_|DB_|POSTGRES_)" | sort
echo "────────────────────────────────────────────────────────────────"
echo ""

# 4. Configuration Alembic
log "⚙️ Configuration Alembic:"
echo "────────────────────────────────────────────────────────────────"
if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend test -f /app/alembic.ini; then
    info "✅ Fichier alembic.ini trouvé"
    echo "Contenu de alembic.ini:"
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend head -20 /app/alembic.ini
else
    error "❌ Fichier alembic.ini introuvable"
fi
echo "────────────────────────────────────────────────────────────────"
echo ""

# 5. État de la table alembic_version
log "📋 Table alembic_version:"
echo "────────────────────────────────────────────────────────────────"
if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres psql -U ajt_user -d ajt_db -c "SELECT * FROM alembic_version;" 2>/dev/null; then
    info "✅ Table alembic_version accessible"
else
    warn "⚠️ Table alembic_version introuvable - Alembic non initialisé"
    echo "Pour initialiser:"
    echo "  docker compose exec backend alembic stamp head"
fi
echo "────────────────────────────────────────────────────────────────"
echo ""

# 6. Migrations dans le container
log "📦 Migrations dans le container (/app/alembic/versions):"
echo "────────────────────────────────────────────────────────────────"
$DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend ls -la /app/alembic/versions/ 2>/dev/null || warn "Répertoire des migrations introuvable dans le container"
echo "────────────────────────────────────────────────────────────────"
echo ""

# 7. Migrations sur l'hôte
log "💾 Migrations sur l'hôte (backend/alembic/versions):"
echo "────────────────────────────────────────────────────────────────"
if [ -d "backend/alembic/versions" ]; then
    ls -la backend/alembic/versions/
    echo ""
    echo "Nombre de migrations: $(ls backend/alembic/versions/*.py 2>/dev/null | wc -l)"
else
    warn "⚠️ Répertoire backend/alembic/versions introuvable sur l'hôte"
fi
echo "────────────────────────────────────────────────────────────────"
echo ""

# 8. État actuel d'Alembic
log "🗃️ État actuel d'Alembic:"
echo "────────────────────────────────────────────────────────────────"
if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic current --verbose 2>/dev/null; then
    info "✅ Alembic opérationnel"
else
    warn "⚠️ Problème avec Alembic"
fi
echo "────────────────────────────────────────────────────────────────"
echo ""

# 9. Historique des migrations
log "📜 Historique des migrations:"
echo "────────────────────────────────────────────────────────────────"
$DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic history --indicate-current 2>/dev/null || warn "Impossible d'afficher l'historique"
echo "────────────────────────────────────────────────────────────────"
echo ""

# 10. Structure de la table users
log "👥 Structure actuelle de la table users:"
echo "────────────────────────────────────────────────────────────────"
$DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres psql -U ajt_user -d ajt_db -c "\d users" 2>/dev/null || error "Impossible d'accéder à la table users"
echo "────────────────────────────────────────────────────────────────"
echo ""

# 11. Vérification des colonnes spécifiques
log "🔍 Vérification des nouvelles colonnes:"
echo "────────────────────────────────────────────────────────────────"
echo "Colonnes dans la table users:"
$DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres psql -U ajt_user -d ajt_db -t -c "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position;" 2>/dev/null || warn "Impossible de lister les colonnes"
echo "────────────────────────────────────────────────────────────────"
echo ""

# 12. Test de génération de migration
log "🧪 Test de génération de migration (dry-run):"
echo "────────────────────────────────────────────────────────────────"
echo "Simulation de génération de migration..."
if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T backend alembic revision --autogenerate -m "test_diagnostic" --sql; then
    info "✅ Génération de migration possible"
else
    warn "⚠️ Problème lors de la génération de migration"
fi
echo "────────────────────────────────────────────────────────────────"
echo ""

# 13. Logs du backend
log "📋 Logs récents du backend (20 dernières lignes):"
echo "────────────────────────────────────────────────────────────────"
$DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" logs --tail=20 backend
echo "────────────────────────────────────────────────────────────────"
echo ""

# 14. Recommandations
log "💡 Recommandations:"
echo "════════════════════════════════════════════════════════════════"

# Vérifier si alembic_version existe
if ! $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T postgres psql -U ajt_user -d ajt_db -c "SELECT 1 FROM alembic_version LIMIT 1;" >/dev/null 2>&1; then
    warn "1. Initialiser Alembic:"
    echo "   docker compose exec backend alembic stamp head"
    echo ""
fi

# Vérifier les volumes
echo "2. Vérifier les volumes Docker:"
echo "   docker volume ls | grep ajtpro"
echo ""

# Vérifier la configuration
echo "3. Si les migrations ne s'appliquent pas:"
echo "   - Vérifier la configuration de la base de données dans alembic.ini"
echo "   - Vérifier que les modèles SQLAlchemy sont bien importés"
echo "   - Redémarrer les containers si nécessaire"
echo ""

echo "4. Pour forcer une migration:"
echo "   docker compose exec backend alembic upgrade head"
echo ""

echo "5. Pour voir le SQL qui serait exécuté:"
echo "   docker compose exec backend alembic upgrade head --sql"
echo ""

log "🎯 Diagnostic terminé !"
echo "════════════════════════════════════════════════════════════════"