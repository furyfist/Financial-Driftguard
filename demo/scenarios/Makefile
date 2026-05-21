# FinSight AI — Makefile
# Usage: make <target>
# Run `make help` to see all available commands.

# ── config ─────────────────────────────────────────────────────────────────
PYTHON      := python
VENV        := venv
PIP         := $(VENV)/bin/pip
PYTEST      := $(VENV)/bin/pytest
UVICORN     := $(VENV)/bin/uvicorn

# Windows compatibility — use Scripts/ instead of bin/
ifeq ($(OS),Windows_NT)
    PIP     := $(VENV)/Scripts/pip
    PYTEST  := $(VENV)/Scripts/pytest
    UVICORN := $(VENV)/Scripts/uvicorn
    PYTHON  := $(VENV)/Scripts/python
endif

.DEFAULT_GOAL := help

# ── help ───────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  FinSight AI — Available Commands"
	@echo "  ─────────────────────────────────────────────────────"
	@echo "  Setup"
	@echo "    make setup          Full first-time setup (venv + deps + env)"
	@echo "    make install        Install Python deps into existing venv"
	@echo "    make env            Copy .env.example → .env (edit manually)"
	@echo ""
	@echo "  ML / Training"
	@echo "    make train          Build labels + train regime classifier"
	@echo "    make backtest       Run walk-forward backtest validation"
	@echo "    make sanity         Quick sanity check (no server needed)"
	@echo ""
	@echo "  Development"
	@echo "    make serve          Start FastAPI backend (hot reload)"
	@echo "    make ui             Start React dashboard (http://localhost:5173)"
	@echo "    make phoenix        Start Phoenix observability (Docker required)"
	@echo "    make seed           Seed demo data (backend must be running)"
	@echo ""
	@echo "  Testing"
	@echo "    make test           Run full test suite"
	@echo "    make test-watch     Run tests in watch mode"
	@echo ""
	@echo "  Demo"
	@echo "    make demo           Run all 3 scenarios interactively"
	@echo "    make demo-auto      Run all 3 scenarios automatically (CI mode)"
	@echo "    make demo-covid     Run COVID crash scenario only"
	@echo "    make demo-hike      Run rate hike scenario only"
	@echo "    make demo-decay     Run normal decay scenario only"
	@echo ""
	@echo "  Maintenance"
	@echo "    make clean          Remove generated files and cache"
	@echo "    make reset-db       Delete SQLite database (requires re-seed)"
	@echo ""


# ── setup ──────────────────────────────────────────────────────────────────
.PHONY: setup
setup: env
	@echo "\n  Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "  Installing dependencies..."
	$(PIP) install --upgrade pip --quiet
	$(PIP) install -r requirements.txt --quiet
	$(PIP) install -e . --quiet
	@echo "\n  ✅  Setup complete."
	@echo "  Next steps:"
	@echo "    1. Edit .env — add your GROQ_API_KEY and FRED_API_KEY"
	@echo "    2. make train         (build regime classifier)"
	@echo "    3. make serve         (start backend in a new terminal)"
	@echo "    4. make seed          (seed demo data)"
	@echo "    5. make ui            (start dashboard in another terminal)"
	@echo "    6. make demo          (run the full demo)"

.PHONY: install
install:
	$(PIP) install --upgrade pip --quiet
	$(PIP) install -r requirements.txt --quiet
	$(PIP) install -e . --quiet
	@echo "  ✅  Dependencies installed."

.PHONY: env
env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "  ✅  .env created from .env.example"; \
		echo "  ⚠️   Edit .env and add your API keys before running."; \
	else \
		echo "  .env already exists — skipping copy."; \
	fi


# ── ml / training ──────────────────────────────────────────────────────────
.PHONY: train
train:
	@echo "\n  Building regime labels..."
	$(PYTHON) scripts/build_regime_labels.py
	@echo "\n  Training regime classifier..."
	$(PYTHON) scripts/train_regime_classifier.py
	@echo "\n  ✅  Regime classifier trained."

.PHONY: backtest
backtest:
	@echo "\n  Running walk-forward backtest..."
	$(PYTHON) scripts/run_backtest.py

.PHONY: sanity
sanity:
	@echo "\n  Running sanity check (no server required)..."
	$(PYTHON) scripts/sanity_check.py


# ── development ────────────────────────────────────────────────────────────
.PHONY: serve
serve:
	@echo "\n  Starting FastAPI backend on http://localhost:8000"
	@echo "  API docs: http://localhost:8000/docs\n"
	$(UVICORN) driftguard.api.main:app --reload

.PHONY: ui
ui:
	@echo "\n  Starting React dashboard on http://localhost:5173\n"
	cd dashboard && npm run dev

.PHONY: phoenix
phoenix:
	@echo "\n  Starting Phoenix observability at http://localhost:6006\n"
	docker compose up phoenix

.PHONY: seed
seed:
	@echo "\n  Seeding demo data (backend must be running on :8000)..."
	$(PYTHON) demo/lending_club.py
	@echo "\n  ✅  Demo data seeded."


# ── testing ────────────────────────────────────────────────────────────────
.PHONY: test
test:
	@echo "\n  Running test suite..."
	$(PYTEST) tests/ -v

.PHONY: test-watch
test-watch:
	$(PYTEST) tests/ -v --tb=short -f


# ── demo ───────────────────────────────────────────────────────────────────
.PHONY: demo
demo:
	@echo "\n  Starting FinSight AI full demo (interactive)..."
	$(PYTHON) scripts/demo_full.py

.PHONY: demo-auto
demo-auto:
	@echo "\n  Starting FinSight AI full demo (auto mode)..."
	$(PYTHON) scripts/demo_full.py --auto --delay 2

.PHONY: demo-covid
demo-covid:
	@echo "\n  Running COVID crash scenario..."
	$(PYTHON) demo/scenarios/covid_crash.py

.PHONY: demo-hike
demo-hike:
	@echo "\n  Running rate hike scenario..."
	$(PYTHON) demo/scenarios/rate_hike_2017.py

.PHONY: demo-decay
demo-decay:
	@echo "\n  Running normal decay scenario..."
	$(PYTHON) demo/scenarios/normal_decay.py


# ── maintenance ────────────────────────────────────────────────────────────
.PHONY: clean
clean:
	@echo "\n  Cleaning generated files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	rm -rf finsight/reports/output/*.pdf 2>/dev/null || true
	@echo "  ✅  Clean complete."

.PHONY: reset-db
reset-db:
	@echo "\n  ⚠️   This will delete driftguard.db and all stored data."
	@read -p "  Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		rm -f driftguard.db; \
		echo "  ✅  Database deleted. Run 'make seed' to re-seed."; \
	else \
		echo "  Cancelled."; \
	fi
