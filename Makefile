PYTHON := python3
VENV := backend/.venv
PIP := $(VENV)/bin/pip
USER := postgres
PYTHON_VENV := $(VENV)/bin/python
MSG := "Auto migration"
DC := docker compose
SERVICE ?=

.PHONY: help docker-build docker-up docker-down docker-logs docker-build-% docker-up-% docker-down-% docker-logs-% shell shell-% alembic-init alembic-migrate alembic-upgrade alembic-current alembic-history clean-branches frontend-dev npm-fix npm-clean docker-build-fix

help:
	@echo "Commandes disponibles:"
	@echo "  docker-build [SERVICE=nom] - Construire les images Docker"
	@echo "  docker-build-fix          - Construire avec correction des dépendances"
	@echo "  docker-up [SERVICE=nom]    - Démarrer les services"
	@echo "  docker-down [SERVICE=nom]  - Arrêter les services"
	@echo "  docker-logs [SERVICE=nom]  - Voir les logs"
	@echo "  npm-fix                   - Corriger les dépendances npm"
	@echo "  npm-clean                 - Nettoyage complet npm"
	@echo "  frontend-dev              - Démarrer le frontend en mode développement"
	@echo "  frontend-build            - Construire le frontend"
	@echo "  frontend-logs             - Voir les logs du frontend"
	@echo "  shell-<service>           - Ouvrir un shell dans un conteneur"
	@echo "  alembic-init              - Initialiser Alembic (une seule fois)"
	@echo "  alembic-migrate           - Créer une nouvelle migration"
	@echo "  alembic-upgrade           - Appliquer les migrations"
	@echo "  alembic-current           - Voir la version actuelle"
	@echo "  alembic-history           - Voir l'historique des migrations"
	@echo "  clean-branches            - Supprimer les branches git locales"
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
	docker compose run --rm backend alembic revision --autogenerate -m "$(MSG)"
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

# Commandes de développement
dev-setup: docker-build docker-up alembic-upgrade
	@echo "Environnement de développement prêt!"
	@echo "  - Frontend: http://localhost:3000"
	@echo "  - Backend: http://localhost:5001"
	@echo "  - Database: localhost:5432"

prod-setup: docker-build docker-up alembic-upgrade
	@echo "Environnement de production prêt!"

dev-frontend: frontend-dev
	@echo "Frontend de développement avec hot-reload démarré"

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