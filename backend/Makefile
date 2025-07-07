PYTHON := python3
VENV := .venv
PIP := $(VENV)/bin/pip

.PHONY: venv install run clean

venv:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install: venv

run: venv
	$(VENV)/bin/python app.py

clean:
	rm -rf $(VENV)
