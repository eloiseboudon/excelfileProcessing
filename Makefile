PYTHON := python3
VENV := backend/.venv
PIP := $(VENV)/bin/pip
USER := postgres
PYTHON_VENV := $(VENV)/bin/python
MSG := "Auto migration"
DC := docker compose
SERVICE ?=

.PHONY: help docker-build docker-up docker-down docker-logs docker-build-% docker-up-% docker-down-% docker-logs-% shell shell-% alembic-init alembic-migrate alembic-upgrade alembic-current alembic-history clean-branches frontend-dev npm-fix npm-clean docker-build-fix implement-tables reset-database check-tables list-brands list-colors network-debug test-connectivity test-api test-frontend test-database test-all fix-network dev-start dev-stop dev-restart-backend dev-restart-frontend dev-logs dev-logs-backend dev-logs-frontend dev-status

help:
	@echo "Commandes disponibles:"
	@echo ""
	@echo "🚀 DÉVELOPPEMENT (Hot-Reload):"
	@echo "  dev-start                 - Démarrer l'environnement de développement"
	@echo "  dev-stop                  - Arrêter l'environnement de développement"
	@echo "  dev-status                - Voir le statut du développement"
	@echo "  dev-logs                  - Voir les logs en temps réel"
	@echo "  dev-restart-backend       - Redémarrer seulement le backend"
	@echo "  dev-restart-frontend      - Redémarrer seulement le frontend"
	@echo ""
	@echo "🐳 DOCKER:"
	@echo "  docker-build [SERVICE=nom] - Construire les images Docker"
	@echo "  docker-build-fix          - Construire avec correction des dépendances"
	@echo "  docker-up [SERVICE=nom]    - Démarrer les services"
	@echo "  docker-down [SERVICE=nom]  - Arrêter les services"
	@echo "  docker-logs [SERVICE=nom]  - Voir les logs"
	@echo ""
	@echo "🌐 FRONTEND:"
	@echo "  npm-fix                   - Corriger les dépendances npm"
	@echo "  npm-clean                 - Nettoyage complet npm"
	@echo "  frontend-dev              - Démarrer le frontend en mode développement"
	@echo "  frontend-build            - Construire le frontend"
	@echo "  frontend-logs             - Voir les logs du frontend"
	@echo ""
	@echo "🗃️ BASE DE DONNÉES:"
	@echo "  alembic-init              - Initialiser Alembic (une seule fois)"
	@echo "  alembic-migrate           - Créer une nouvelle migration"
	@echo "  alembic-upgrade           - Appliquer les migrations"
	@echo "  implement-tables          - Implémenter les tables avec les données initiales"
	@echo "  reset-database            - Réinitialiser complètement la base de données"
	@echo "  check-tables              - Vérifier le contenu des tables"
	@echo ""
	@echo "🧪 TESTS:"
	@echo "  test-connectivity         - Tester la connectivité entre services"
	@echo "  test-api                  - Tester toutes les APIs"
	@echo "  test-all                  - Exécuter tous les tests"
	@echo "  network-debug             - Diagnostiquer les problèmes réseau"
	@echo ""
	@echo "🏗️ SETUP:"
	@echo "  dev-setup                 - Configuration complète pour le développement"
	@echo "  prod-setup                - Configuration pour la production"

# Correction des dépendances npm
npm-fix:
	@echo "=== Correction des dépendances npm ==="
	@echo "Suppression du package-lock.json obsolète..."
	@rm -f frontend/package-lock.json
	@echo "Régénération des dépendances..."
	@cd frontend && npm install
	@echo "Dépendances corrigées ✅"

npm-clean:
	@echo "=== Nettoyage complet npm ==="
	@rm -rf frontend/node_modules frontend/package-lock.json
	@cd frontend && npm install
	@echo "Nettoyage terminé ✅"

# Construction avec correction automatique
docker-build-fix:
	@echo "=== Construction avec correction des dépendances ==="
	@make npm-fix
	@make docker-build

# Docker commands
docker-build:
	$(DC) build $(SERVICE)

docker-up:
	$(DC) up -d $(SERVICE)
	@if [ -z "$(SERVICE)" ]; then \
		echo "Services démarrés:"; \
		echo "  - PostgreSQL: localhost:5432"; \
		echo "  - Backend: localhost:5001"; \
		echo "  - Frontend: http://localhost:3000"; \
	fi

docker-down:
	@if [ -z "$(SERVICE)" ]; then \
		$(DC) down; \
	else \
		$(DC) stop $(SERVICE); \
		$(DC) rm -f $(SERVICE); \
	fi

docker-restart: docker-down docker-up

docker-logs:
	$(DC) logs -f $(SERVICE)

# Frontend specific commands
frontend-build:
	$(DC) build frontend

frontend-dev:
	@echo "Construction de l'image frontend-dev..."
	$(DC) --profile dev build frontend-dev
	@echo "Démarrage du frontend de développement..."
	$(DC) --profile dev up -d frontend-dev
	@echo "Attente du démarrage du serveur..."
	@sleep 5
	@echo "Vérification du statut..."
	@docker compose ps frontend-dev
	@echo "Frontend de développement accessible sur http://localhost:5173"
	@echo "Logs disponibles avec: make frontend-dev-logs"

frontend-dev-logs:
	$(DC) logs -f frontend-dev

frontend-dev-shell:
	$(DC) exec frontend-dev sh

frontend-logs:
	$(DC) logs -f frontend

frontend-stop:
	$(DC) stop frontend frontend-dev

frontend-restart:
	$(DC) restart frontend

frontend-dev-debug:
	@echo "=== Diagnostic complet du frontend-dev ==="
	@echo "1. Statut du conteneur:"
	@docker compose ps frontend-dev
	@echo -e "\n2. Ports mappés:"
	@docker port ajt_frontend_dev 2>/dev/null || echo "Conteneur non trouvé"
	@echo -e "\n3. Processus dans le conteneur:"
	@docker compose exec frontend-dev ps aux 2>/dev/null || echo "Conteneur non accessible"
	@echo -e "\n4. Ports ouverts dans le conteneur:"
	@docker compose exec frontend-dev netstat -tlnp 2>/dev/null || echo "Conteneur non accessible"
	@echo -e "\n5. Test de connectivité local:"
	@curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:5173 || echo "Service non accessible"
	@echo -e "\n6. Test depuis le conteneur:"
	@docker compose exec frontend-dev curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:5173 2>/dev/null || echo "Test interne échoué"
	@echo -e "\n7. Logs récents:"
	@docker compose logs --tail=20 frontend-dev

frontend-dev-rebuild:
	@echo "=== Reconstruction du frontend-dev ==="
	$(DC) stop frontend-dev 2>/dev/null || true
	$(DC) rm -f frontend-dev 2>/dev/null || true
	$(DC) --profile dev build --no-cache frontend-dev
	@echo "=== Redémarrage du service ==="
	$(DC) --profile dev up -d frontend-dev
	@echo "=== Attente du démarrage ==="
	@sleep 5
	@echo "=== Diagnostic ==="
	@make frontend-dev-debug

frontend-dev-fix:
	@echo "=== Correction complète du frontend-dev ==="
	@echo "1. Arrêt du service"
	@$(DC) stop frontend-dev 2>/dev/null || true
	@$(DC) rm -f frontend-dev 2>/dev/null || true
	@echo "2. Nettoyage des images"
	@docker rmi -f $$(docker images -q "*frontend-dev*") 2>/dev/null || true
	@echo "3. Reconstruction"
	@$(DC) --profile dev build --no-cache frontend-dev
	@echo "4. Redémarrage"
	@$(DC) --profile dev up -d frontend-dev
	@echo "5. Vérification"
	@sleep 8
	@make frontend-dev-debug

# Backend specific commands
backend-build:
	$(DC) build backend

backend-logs:
	$(DC) logs -f backend

backend-restart:
	$(DC) restart backend

# Database commands
db-logs:
	$(DC) logs -f postgres

db-backup:
	docker compose exec postgres pg_dump -U postgres ajtpro > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup créé: backup_$(shell date +%Y%m%d_%H%M%S).sql"

db-restore:
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Usage: make db-restore BACKUP_FILE=backup_file.sql"; \
		exit 1; \
	fi
	cat $(BACKUP_FILE) | docker compose exec -T postgres psql -U postgres ajtpro

# Règles génériques pour un service
docker-build-%:
	$(DC) build $*

docker-up-%:
	$(DC) up -d $*

docker-down-%:
	$(DC) stop $*
	$(DC) rm -f $*

docker-logs-%:
	$(DC) logs -f $*

shell-%:
	docker compose exec $* sh

# Commandes Alembic (toutes dans Docker)
alembic-init:
	docker compose run --rm backend alembic init alembic
	@echo "Alembic initialisé. Pensez à configurer env.py"

alembic-migrate:
	docker compose run --rm backend alembic revision --autogenerate -m $(MSG)
	@echo "Migration créée avec le message: $(MSG)"

alembic-upgrade:
	docker compose exec backend alembic upgrade head
	@echo "Migrations appliquées"

alembic-downgrade:
	docker compose exec backend alembic downgrade -1
	@echo "Migration précédente annulée"

alembic-current:
	docker compose exec backend alembic current

alembic-history:
	docker compose exec backend alembic history --verbose

# Commandes de gestion des données
implement-tables:
	@echo "=== Implémentation des tables avec les données initiales ==="
	docker compose exec backend python implement_tables.py
	@echo "Tables implémentées avec succès ✅"

implement-tables-run:
	@echo "=== Implémentation des tables (avec run si le conteneur n'est pas démarré) ==="
	docker compose run --rm backend python implement_tables.py
	@echo "Tables implémentées avec succès ✅"

reset-database:
	@echo "=== Réinitialisation complète de la base de données ==="
	@echo "⚠️  ATTENTION: Ceci va supprimer toutes les données existantes!"
	@read -p "Êtes-vous sûr de vouloir continuer? (y/N): " confirm && [ "$confirm" = "y" ] || exit 1
	@make implement-tables
	@echo "Base de données réinitialisée ✅"

populate-db: implement-tables
	@echo "Alias pour implement-tables"

seed-database: implement-tables
	@echo "Alias pour implement-tables"

# Commandes de vérification des données
check-tables:
	@echo "=== Vérification des tables ==="
	@echo "Suppliers:"
	@docker compose exec backend python -c "import psycopg2; import os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM suppliers'); print(f'  - {cur.fetchone()[0]} suppliers'); cur.close(); conn.close()"
	@echo "Brands:"
	@docker compose exec backend python -c "import psycopg2; import os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM brands'); print(f'  - {cur.fetchone()[0]} brands'); cur.close(); conn.close()"
	@echo "Colors:"
	@docker compose exec backend python -c "import psycopg2; import os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM colors'); print(f'  - {cur.fetchone()[0]} colors'); cur.close(); conn.close()"
	@echo "Device Types:"
	@docker compose exec backend python -c "import psycopg2; import os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM device_types'); print(f'  - {cur.fetchone()[0]} device types'); cur.close(); conn.close()"

list-brands:
	@echo "=== Liste des marques ==="
	@docker compose exec backend python -c "import psycopg2; import os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cur = conn.cursor(); cur.execute('SELECT brand FROM brands ORDER BY brand'); [print(f'  - {row[0]}') for row in cur.fetchall()]; cur.close(); conn.close()"

# Diagnostic réseau et connectivité
network-debug:
	@echo "=== Diagnostic réseau Docker ==="
	@echo "1. Réseaux Docker:"
	@docker network ls
	@echo -e "\n2. Conteneurs et leurs IPs:"
	@docker compose ps
	@echo -e "\n3. Test de connectivité interne:"
	@docker compose exec frontend ping -c 3 backend 2>/dev/null || echo "❌ Frontend ne peut pas joindre le backend"
	@docker compose exec backend ping -c 3 postgres 2>/dev/null || echo "❌ Backend ne peut pas joindre postgres"
	@echo -e "\n4. Ports ouverts sur l'hôte:"
	@netstat -tlnp 2>/dev/null | grep -E "(3000|5001|5432)" || echo "❌ Ports non ouverts"
	@echo -e "\n5. Test d'accès externe:"
	@curl -I http://localhost:3000 2>/dev/null || echo "❌ Frontend non accessible"
	@curl -I http://localhost:5001 2>/dev/null || echo "❌ Backend non accessible"

test-connectivity:
	@echo "=== Test de connectivité ==="
	@echo "Frontend -> Backend:"
	@docker compose exec frontend curl -I http://backend:5001 2>/dev/null && echo "✅ Frontend -> Backend OK" || echo "❌ Frontend -> Backend KO"
	@echo "Backend -> Database:"
	@docker compose exec backend python -c "import psycopg2; import os; psycopg2.connect(os.getenv('DATABASE_URL')); print('✅ Backend -> Database OK')" 2>/dev/null || echo "❌ Backend -> Database KO"
	@echo "External -> Frontend:"
	@curl -I http://localhost:3000 2>/dev/null && echo "✅ External -> Frontend OK" || echo "❌ External -> Frontend KO"
	@echo "External -> Backend:"
	@curl -I http://localhost:5001 2>/dev/null && echo "✅ External -> Backend OK" || echo "❌ External -> Backend KO"
	@echo "Backend API endpoints:"
	@curl -s http://localhost:5001/health 2>/dev/null | grep -q "healthy" && echo "✅ Health endpoint OK" || echo "❌ Health endpoint KO"
	@curl -s http://localhost:5001/api/brands 2>/dev/null | grep -q "brands" && echo "✅ Brands API OK" || echo "❌ Brands API KO"
	@curl -s http://localhost:5001/api/colors 2>/dev/null | grep -q "colors" && echo "✅ Colors API OK" || echo "❌ Colors API KO"

test-api:
	@echo "=== Test des APIs ==="
	@echo "Health Check:"
	@curl -s http://localhost:5001/health | python -m json.tool 2>/dev/null || echo "❌ Health API non disponible"
	@echo -e "\nBrands API:"
	@curl -s http://localhost:5001/api/brands | python -m json.tool 2>/dev/null || echo "❌ Brands API non disponible"
	@echo -e "\nColors API:"
	@curl -s http://localhost:5001/api/colors | python -m json.tool 2>/dev/null || echo "❌ Colors API non disponible"
	@echo -e "\nSuppliers API:"
	@curl -s http://localhost:5001/api/suppliers | python -m json.tool 2>/dev/null || echo "❌ Suppliers API non disponible"

test-frontend:
	@echo "=== Test du Frontend ==="
	@echo "Accès au frontend:"
	@curl -I http://localhost:3000 2>/dev/null && echo "✅ Frontend accessible" || echo "❌ Frontend non accessible"
	@echo "Test JavaScript (si disponible):"
	@curl -s http://localhost:3000 | grep -q "root" && echo "✅ Index.html chargé" || echo "❌ Index.html non chargé"

test-database:
	@echo "=== Test de la base de données ==="
	@echo "Connexion à la base de données:"
	@docker compose exec backend python -c "import psycopg2; import os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cur = conn.cursor(); cur.execute('SELECT 1'); print('✅ Database connection OK'); cur.close(); conn.close()" 2>/dev/null || echo "❌ Database connection failed"
	@echo "Test des données:"
	@docker compose exec backend python -c "import psycopg2; import os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM brands'); print(f'✅ Brands in DB: {cur.fetchone()[0]}'); cur.close(); conn.close()" 2>/dev/null || echo "❌ No brands data"

test-all: test-connectivity test-api test-frontend test-database
	@echo "=== Tous les tests terminés ==="

fix-network:
	@echo "=== Tentative de correction réseau ==="
	@echo "Redémarrage des services avec reconstruction du réseau..."
	@docker compose down
	@docker network prune -f
	@docker compose up -d
	@echo "Attente du démarrage des services..."
	@sleep 10
	@make test-connectivity

# Commandes de développement
dev-setup: docker-build docker-up alembic-upgrade implement-tables
	@echo "Environnement de développement prêt!"
	@echo "  - Frontend: http://localhost:3000"
	@echo "  - Backend: http://localhost:5001"
	@echo "  - Database: localhost:5432"
	@echo "  - Tables initialisées avec les données de référence ✅"

dev-setup-quick: docker-up alembic-upgrade implement-tables
	@echo "Démarrage rapide (sans rebuild) terminé!"

prod-setup: docker-build docker-up alembic-upgrade implement-tables
	@echo "Environnement de production prêt!"

# Commandes spéciales pour le développement
dev-start:
	@echo "=== Démarrage environnement de développement ==="
	@echo "🔧 Démarrage des services backend + database..."
	@$(DC) up -d postgres backend
	@echo "⏳ Attente du backend..."
	@sleep 5
	@echo "🎨 Démarrage du frontend avec hot-reload..."
	@$(DC) --profile dev up -d frontend-dev
	@echo "✅ Environnement de développement prêt:"
	@echo "  - Backend (hot-reload): http://localhost:5001"
	@echo "  - Frontend (hot-reload): http://localhost:5173"
	@echo "  - Database: localhost:5432"
	@echo ""
	@echo "💡 Modifications automatiquement détectées:"
	@echo "  - Backend: Toute modification .py dans backend/"
	@echo "  - Frontend: Toute modification dans frontend/src/"

dev-stop:
	@echo "=== Arrêt environnement de développement ==="
	@$(DC) stop backend postgres frontend-dev
	@echo "✅ Environnement de développement arrêté"

dev-restart-backend:
	@echo "=== Redémarrage backend seulement ==="
	@$(DC) restart backend
	@echo "✅ Backend redémarré"

dev-restart-frontend:
	@echo "=== Redémarrage frontend seulement ==="
	@$(DC) --profile dev restart frontend-dev
	@echo "✅ Frontend redémarré"

dev-logs:
	@echo "=== Logs du développement ==="
	@$(DC) logs -f backend frontend-dev

dev-logs-backend:
	@echo "=== Logs backend ==="
	@$(DC) logs -f backend

dev-logs-frontend:
	@echo "=== Logs frontend ==="
	@$(DC) logs -f frontend-dev

dev-status:
	@echo "=== Statut développement ==="
	@echo "Services actifs:"
	@$(DC) ps postgres backend frontend-dev
	@echo ""
	@echo "Test de connectivité:"
	@curl -s http://localhost:5001/health >/dev/null 2>&1 && echo "✅ Backend: OK" || echo "❌ Backend: KO"
	@curl -s http://localhost:5173 >/dev/null 2>&1 && echo "✅ Frontend: OK" || echo "❌ Frontend: KO"

dev-reset: docker-down
	docker volume rm $$(docker volume ls -q | grep postgres_data) 2>/dev/null || true
	$(MAKE) dev-setup

# Shell dans les conteneurs
shell-backend:
	docker compose exec backend bash

shell-frontend:
	docker compose exec frontend sh

shell-postgres:
	docker compose exec postgres psql -U postgres -d ajtpro

# Tests
test-backend:
	docker compose exec backend python -m pytest

test-frontend:
	docker compose exec frontend npm test

# Monitoring
status:
	$(DC) ps

health:
	@echo "Vérification de l'état des services..."
	@docker compose exec backend curl -f http://localhost:5001/health || echo "Backend: ❌"
	@curl -f http://localhost:3000 > /dev/null 2>&1 && echo "Frontend: ✅" || echo "Frontend: ❌"
	@docker compose exec postgres pg_isready -U postgres > /dev/null 2>&1 && echo "Database: ✅" || echo "Database: ❌"

# Nettoyage
clean:
	$(DC) down -v
	docker system prune -f
	rm -rf $(VENV)

clean-frontend:
	$(DC) down frontend frontend-dev
	docker rmi -f $$(docker images -q "*frontend*") 2>/dev/null || true

clean-all: clean
	docker system prune -a -f
	docker volume prune -f

# Git utilities
clean-branches:
	git branch | grep -v -E "(main|dev|\*)" | xargs git branch -d