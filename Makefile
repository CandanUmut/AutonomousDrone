VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: setup sim mission test lint

setup:
	python3.11 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e software/companion[dev]

sim:
	./scripts/sim_px4.sh

mission:
	./scripts/run_mission_demo.sh

test:
	$(PYTHON) -m pytest software/companion/tests

lint:
	$(PYTHON) -m ruff format --check software/companion/src software/companion/tests
	$(PYTHON) -m ruff check software/companion/src software/companion/tests
	$(PYTHON) -m mypy software/companion/src
