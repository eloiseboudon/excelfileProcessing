PYTHON := python3
VENV := backend/.venv
PIP := $(VENV)/bin/pip
USER := postgres
PYTHON_VENV := $(VENV)/bin/python
MSG := "Auto migration"
DC := docker compose

# git branch | grep -v -E "(main|dev|\*)" | xargs git branch -d

.PHONY: db-create db-implement_tables alembic-init alembic-migrate alembic-upgrade alembic-current docker-build docker-up docker-down docker-logs

# Commandes de base de données
db-create:
	psql -U $(USER) -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='ajtpro'" | grep -q 1 || psql -U $(USER) -d postgres -c "CREATE DATABASE ajtpro"

db-implement_tables:
	$(PYTHON_VENV) backend/implement_tables.py

# Commandes Alembic - VERSION ABSOLUE (RECOMMANDÉE)
alembic-init: venv
	cd backend && $(CURDIR)/$(PYTHON_VENV) -m alembic init alembic

alembic-migrate:
	$(DC) run --rm backend alembic revision --autogenerate -m "$(MSG)"
	@echo "Migration created with message: $(MSG)"

alembic-upgrade:
	$(DC) run --rm backend alembic upgrade head

alembic-current: 
	$(DC) run --rm backend alembic current

alembic-history:
	$(DC) run --rm backend alembic history --verbose

debug-env:
	@echo "Checking environment..."
	@ls -la backend/.venv/bin/ | grep python || echo "Python not found"
	@$(PYTHON_VENV) -m pip list | grep alembic || echo "Alembic not installed"

# Docker commands
docker-build:
	$(DC) build

docker-up:
	$(DC) up -d

docker-down:
	$(DC) down

docker-logs:
	$(DC) logs -f
