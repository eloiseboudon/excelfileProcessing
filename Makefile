PYTHON := python3
VENV := backend/.venv
PIP := $(VENV)/bin/pip

.PHONY: db-create db-create_tables venv install run clean 

db-create:
	psql -U postgres -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='ajtpro'" | grep -q 1 || psql -U eloise -d postgres -c "CREATE DATABASE ajtpro"

db-create_tables:
	$(VENV)/bin/python backend/create_tables.py

venv:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt

install: venv

run: venv
	$(VENV)/bin/python backend/app.py

clean:
	rm -rf $(VENV)
