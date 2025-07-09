PYTHON := python3
VENV := backend/.venv
PIP := $(VENV)/bin/pip
USER := postgres
PYTHON_VENV := $(VENV)/bin/python

.PHONY: db-create db-create_tables venv install run clean alembic-init alembic-migrate alembic-upgrade alembic-current

db-create:
	psql -U $(USER) -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='ajtpro'" | grep -q 1 || psql -U $(USER) -d postgres -c "CREATE DATABASE ajtpro"

db-implement_tables:
	$(PYTHON_VENV) backend/implement_tables.py

venv:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt

install: venv

run: venv
	$(PYTHON_VENV) backend/app.py

clean:
	rm -rf $(VENV)

# Commandes Alembic - VERSION ABSOLUE (RECOMMANDÉE)
alembic-init: venv
	cd backend && $(CURDIR)/$(PYTHON_VENV) -m alembic init alembic

alembic-migrate: venv
	cd backend && $(CURDIR)/$(PYTHON_VENV) -m alembic revision --autogenerate -m "$(MSG)"

alembic-upgrade: venv
	cd backend && $(CURDIR)/$(PYTHON_VENV) -m alembic upgrade head

alembic-current: venv
	cd backend && $(CURDIR)/$(PYTHON_VENV) -m alembic current

alembic-history: venv
	cd backend && $(CURDIR)/$(PYTHON_VENV) -m alembic history

debug-env:
	@echo "Checking environment..."
	@ls -la backend/.venv/bin/ | grep python || echo "Python not found"
	@$(PYTHON_VENV) -m pip list | grep alembic || echo "Alembic not installed"