PYTHON := python3
VENV := backend/.venv
PIP := $(VENV)/bin/pip
DB_USER ?= eloise


.PHONY: db-create db-create_tables venv install run clean migrate migrate-upgrade

db-create:
	psql -U $(DB_USER) -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='ajtpro'" | grep -q 1 || psql -U $(DB_USER) -d postgres -c "CREATE DATABASE ajtpro"
db-create_tables:
	$(VENV)/bin/python backend/create_tables.py

venv:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt

install: venv

run: venv
	$(VENV)/bin/python -m backend.app

migrate:
	$(VENV)/bin/alembic -c backend/alembic.ini revision --autogenerate -m "$(msg)"

migrate-upgrade:
	$(VENV)/bin/alembic -c backend/alembic.ini upgrade head

clean:
	rm -rf $(VENV)
