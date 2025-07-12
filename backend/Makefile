PYTHON := python3
VENV := backend/.venv
PIP := $(VENV)/bin/pip
USER := postgres
PYTHON_VENV := $(VENV)/bin/python
MSG := "Auto migration"
DC := docker compose

# Detect if running inside a container
INSIDE_DOCKER := $(shell [ -f /.dockerenv ] && echo 1)

ifeq ($(INSIDE_DOCKER),1)
RUN_BACKEND :=
EXEC_BACKEND :=
EXEC_POSTGRES := psql -h postgres -U postgres -d ajtpro
PG_DUMP_CMD := pg_dump -h postgres -U postgres ajtpro
else
RUN_BACKEND := $(DC) run --rm backend
EXEC_BACKEND := $(DC) exec backend
EXEC_POSTGRES := $(DC) exec postgres psql -U postgres -d ajtpro
PG_DUMP_CMD := $(DC) exec postgres pg_dump -U postgres ajtpro
endif

.PHONY: help docker-build docker-up docker-down docker-logs alembic-init alembic-migrate alembic-upgrade alembic-current alembic-history db-create-local db-implement-tables clean-branches

help:
	@echo "Commandes disponibles:"
	@echo "  docker-build     - Construire les images Docker"
	@echo "  docker-up        - Démarrer les services"
	@echo "  docker-down      - Arrêter les services"
	@echo "  docker-logs      - Voir les logs"
	@echo "  alembic-init     - Initialiser Alembic (une seule fois)"
	@echo "  alembic-migrate  - Créer une nouvelle migration"
	@echo "  alembic-upgrade  - Appliquer les migrations"
	@echo "  alembic-current  - Voir la version actuelle"
	@echo "  alembic-history  - Voir l'historique des migrations"
	@echo "  clean-branches   - Supprimer les branches git locales"

# Docker commands
docker-build:
	$(DC) build

docker-up:
	$(DC) up -d
	@echo "Services démarrés. PostgreSQL: localhost:5432, Backend: localhost:5001"

docker-down:
	$(DC) down

docker-restart: docker-down docker-up

docker-logs:
	$(DC) logs -f

docker-logs-backend:
	$(DC) logs -f backend

docker-logs-postgres:
	$(DC) logs -f postgres

# Commandes Alembic (toutes dans Docker)
alembic-init:
	$(RUN_BACKEND) alembic init alembic
	@echo "Alembic initialisé. Pensez à configurer env.py"

alembic-migrate:
	$(RUN_BACKEND) alembic revision --autogenerate -m "$(MSG)"
	@echo "Migration créée avec le message: $(MSG)"

alembic-upgrade:
	$(RUN_BACKEND) alembic upgrade head
	@echo "Migrations appliquées"

alembic-downgrade:
	$(RUN_BACKEND) alembic downgrade -1
	@echo "Migration précédente annulée"

alembic-current:
	$(RUN_BACKEND) alembic current

alembic-history:
	$(RUN_BACKEND) alembic history --verbose

# Commandes de développement
dev-setup: docker-build docker-up alembic-upgrade
	@echo "Environnement de développement prêt!"

dev-reset: docker-down
	docker volume rm $$(docker volume ls -q | grep postgres_data) 2>/dev/null || true
	$(MAKE) dev-setup

# Shell dans les conteneurs
shell-backend:
	$(EXEC_BACKEND) bash

shell-postgres:
	$(EXEC_POSTGRES)

shell-implement-tables:
	$(EXEC_BACKEND) python -m implement_tables

# Git utilities
clean-branches:
	git branch | grep -v -E "(main|dev|\*)" | xargs git branch -d

# Nettoyage
clean:
	$(DC) down -v
	docker system prune -f
	rm -rf $(VENV)

# Tests (si vous en avez)
test:
	$(RUN_BACKEND) python -m pytest

# Backup/Restore
backup:
	$(PG_DUMP_CMD) > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore:
	@echo "Usage: make restore BACKUP_FILE=backup_file.sql"
	cat $(BACKUP_FILE) | $(EXEC_POSTGRES)
