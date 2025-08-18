#!/bin/bash

# Script de vérification et correction NPM
# Usage: ./fix-npm-proxy.sh

set -e

APP_DIR="/home/ubuntu/ajtpro"
SERVER_IP="51.77.231.101"

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

echo "🔧 CORRECTION NGINX PROXY MANAGER"
echo "═══════════════════════════════════════════════"

cd "$APP_DIR" || exit 1

# 1. Vérifier l'état des containers AJT Pro
log "🐳 Vérification des containers AJT Pro..."

echo "📊 Statut des containers AJT Pro:"
docker compose -f docker-compose.prod.yml ps

# Vérifier si les containers tournent
frontend_status=$(docker compose -f docker-compose.prod.yml ps frontend | grep -c "Up" || echo "0")
backend_status=$(docker compose -f docker-compose.prod.yml ps backend | grep -c "Up" || echo "0")

if [ "$frontend_status" -eq 0 ]; then
    warn "⚠️ Container frontend non démarré"
    log "🚀 Démarrage du frontend..."
    docker compose -f docker-compose.prod.yml up -d frontend
    sleep 10
fi

if [ "$backend_status" -eq 0 ]; then
    warn "⚠️ Container backend non démarré"
    log "🚀 Démarrage du backend..."
    docker compose -f docker-compose.prod.yml up -d backend
    sleep 10
fi

# 2. Test d'accès direct aux services
log "🧪 Test d'accès direct aux services..."

echo "🌐 Test frontend (port 3000):"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
    info "✅ Frontend accessible localement"
    
    # Test via IP publique
    if timeout 5 curl -s -o /dev/null -w "%{http_code}" "http://$SERVER_IP:3000" | grep -q "200"; then
        info "✅ Frontend accessible via IP publique"
    else
        warn "⚠️ Frontend non accessible via IP publique (firewall?)"
    fi
else
    error "❌ Frontend non accessible localement"
fi

echo ""
echo "🔧 Test backend (port 8000):"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 | grep -q "200"; then
    info "✅ Backend accessible localement"
    
    # Test via IP publique
    if timeout 5 curl -s -o /dev/null -w "%{http_code}" "http://$SERVER_IP:8000" | grep -q "200"; then
        info "✅ Backend accessible via IP publique"
    else
        warn "⚠️ Backend non accessible via IP publique (firewall?)"
    fi
else
    error "❌ Backend non accessible localement"
fi

# 3. Test du domaine actuel
log "🌐 Test du domaine actuel..."

echo "🔍 Test ajtpro.tulip-saas.fr:"
domain_response=$(curl -s https://ajtpro.tulip-saas.fr || echo "erreur")
echo "Réponse: $domain_response"

if echo "$domain_response" | grep -q '"version"'; then
    warn "⚠️ Le domaine renvoie la réponse de Nginx Proxy Manager (pas votre app)"
    echo "    Cela signifie que le proxy host n'est pas configuré correctement"
else
    info "✅ Le domaine semble pointer vers votre application"
fi

# 4. Vérification NPM
log "🔀 Vérification de Nginx Proxy Manager..."

if docker ps | grep -q "nginx-proxy-manager"; then
    info "✅ Nginx Proxy Manager en cours d'exécution"
    
    echo "📋 Informations NPM:"
    docker ps | grep "nginx-proxy-manager"
    
else
    warn "⚠️ Nginx Proxy Manager non trouvé"
fi

# 5. Instructions de configuration
echo ""
echo "═══════════════════════════════════════════════"
log "📋 INSTRUCTIONS DE CONFIGURATION NPM"

echo ""
echo "🔗 1. Accédez à l'interface NPM:"
echo "   URL: http://$SERVER_IP:81"
echo "   Login: admin@example.com"
echo "   Password: changeme (changez-le immédiatement!)"

echo ""
echo "🔧 2. Configuration du Proxy Host pour le FRONTEND:"
echo "   • Cliquez sur 'Proxy Hosts' → 'Add Proxy Host'"
echo "   • Domain Names: ajtpro.tulip-saas.fr"
echo "   • Scheme: http"
echo "   • Forward Hostname/IP: localhost"
echo "   • Forward Port: 3000"
echo "   • Cache Assets: ✅ Activé"
echo "   • Block Common Exploits: ✅ Activé"

echo ""
echo "🔧 3. Configuration du Proxy Host pour l'API:"
echo "   • Cliquez sur 'Add Proxy Host' (nouveau)"
echo "   • Domain Names: ajtpro.api.tulip-saas.fr"
echo "   • Scheme: http"
echo "   • Forward Hostname/IP: localhost"
echo "   • Forward Port: 8000"
echo "   • Cache Assets: ❌ Désactivé"
echo "   • Block Common Exploits: ✅ Activé"

echo ""
echo "🔒 4. SSL (optionnel):"
echo "   • Dans chaque proxy host, onglet 'SSL'"
echo "   • Request a new SSL Certificate with Let's Encrypt"
echo "   • Force SSL: ✅ Activé"
echo "   • Email: votre@email.com"

echo ""
echo "🧪 5. Test après configuration:"
echo "   • Frontend: https://ajtpro.tulip-saas.fr"
echo "   • API: https://ajtpro.api.tulip-saas.fr"

# 6. Configuration automatique VITE_API_BASE
echo ""
log "📝 Préparation de la configuration finale..."

# Créer le script de finalisation
cat > finalize-domain-config.sh << 'EOF'
#!/bin/bash

echo "🔄 FINALISATION DE LA CONFIGURATION DOMAINES"
echo "═══════════════════════════════════════════════"

# Mise à jour de la configuration pour utiliser les domaines HTTPS
cat > .env << 'ENVEOF'
# Configuration finale AJT Pro avec domaines HTTPS
VITE_API_BASE=https://ajtpro.api.tulip-saas.fr
POSTGRES_DB=ajt_db
POSTGRES_USER=ajt_user
POSTGRES_PASSWORD=ajt_password
FLASK_ENV=production
FLASK_DEBUG=0
ENVEOF

# Mise à jour docker-compose.prod.yml
cat > docker-compose.prod.yml << 'COMPOSEEOF'
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ajt_backend_prod
    environment:
      FLASK_ENV: production
      FLASK_DEBUG: 0
      FRONTEND_URL: https://ajtpro.tulip-saas.fr
      CORS_ORIGINS: "https://ajtpro.tulip-saas.fr,http://localhost:3000"
      POSTGRES_DB: ajt_db
      POSTGRES_USER: ajt_user
      POSTGRES_PASSWORD: ajt_password
      POSTGRES_HOST: postgres_prod
      POSTGRES_PORT: 5432
    command: gunicorn -w 4 -b 0.0.0.0:5001 app:app
    ports:
      - "8000:5001"
    depends_on:
      - postgres
    networks:
      - ajt-network
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_BASE: "https://ajtpro.api.tulip-saas.fr"
    container_name: ajt_frontend_prod
    environment:
      - VITE_API_BASE=https://ajtpro.api.tulip-saas.fr
    ports:
      - "3000:80"
    networks:
      - ajt-network
    restart: unless-stopped
    depends_on:
      - backend

  postgres:
    image: postgres:16
    container_name: postgres_prod
    restart: always
    environment:
      POSTGRES_DB: ajt_db
      POSTGRES_USER: ajt_user
      POSTGRES_PASSWORD: ajt_password
    volumes:
      - ajtpro_postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - ajt-network

volumes:
  ajtpro_postgres_data:

networks:
  ajt-network:
    name: ajtpro_default
    external: true
COMPOSEEOF

echo "✅ Configuration mise à jour pour HTTPS"

# Redéploiement
echo "🚀 Redéploiement avec configuration HTTPS..."
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build --no-cache frontend
docker compose -f docker-compose.prod.yml up -d

echo "⏳ Attente du démarrage..."
sleep 15

echo "🧪 Test final:"
curl -I https://ajtpro.tulip-saas.fr

echo ""
echo "🎉 Configuration finale terminée !"
echo "🌐 Votre application: https://ajtpro.tulip-saas.fr"
echo "🔧 Votre API: https://ajtpro.api.tulip-saas.fr"
EOF

chmod +x finalize-domain-config.sh

echo ""
info "📄 Script 'finalize-domain-config.sh' créé"
echo "   À lancer APRÈS avoir configuré NPM avec SSL"

echo ""
echo "═══════════════════════════════════════════════"
log "🎯 PROCHAINES ÉTAPES:"

echo ""
echo "1. 🔧 Configurez NPM maintenant: http://$SERVER_IP:81"
echo "2. 🧪 Testez que les domaines pointent vers votre app"
echo "3. 🚀 Lancez: ./finalize-domain-config.sh"

echo ""
log "✅ Diagnostic terminé !"