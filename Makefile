# ============================================================
# Parking Reservation System — developer commands
#
#   make setup    one-time end-to-end setup (deps, DBs, RAG index)
#   make start    run the app (Admin API + User UI + Admin UI)
#
# Run `make help` to see every command.
# ============================================================

SHELL := /bin/bash

# Override on the CLI, e.g. `make start API_PORT=9000`
API_PORT      ?= 8000
USER_UI_PORT  ?= 8501
ADMIN_UI_PORT ?= 8502
OLLAMA_MODEL  ?= gemma4:31b-cloud
OLLAMA_URL    ?= http://localhost:11434

.DEFAULT_GOAL := help

.PHONY: help setup start stop chat api user-ui admin-ui \
        install env ollama-check rag-index \
        db-up db-down db-reset db-logs test clean

help: ## Show this help
	@echo "Parking Reservation System"
	@echo ""
	@echo "  First time:  make setup    then    make start"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ------------------------------------------------------------
# Headline commands
# ------------------------------------------------------------

setup: env install db-up ollama-check rag-index ## One-time end-to-end setup
	@echo ""
	@echo "✅ Setup complete."
	@echo "   Start the app with:  make start"
	@echo "   Or the CLI chat with:  make chat"

start: ## Run Admin API + User UI + Admin UI together (Ctrl-C stops all)
	@echo "Starting services (Ctrl-C to stop all):"
	@echo "  → Admin API : http://localhost:$(API_PORT)/docs"
	@echo "  → User UI   : http://localhost:$(USER_UI_PORT)"
	@echo "  → Admin UI  : http://localhost:$(ADMIN_UI_PORT)"
	@trap 'kill 0' INT TERM; \
		uv run uvicorn src.api.main:app --port $(API_PORT) & \
		API_BASE_URL=http://localhost:$(API_PORT) uv run streamlit run src/ui/streamlit_app.py --server.port $(USER_UI_PORT) --server.headless true & \
		API_BASE_URL=http://localhost:$(API_PORT) uv run streamlit run src/ui/admin_app.py --server.port $(ADMIN_UI_PORT) --server.headless true & \
		wait

chat: ## Run the interactive CLI chat assistant
	uv run python -m src.main

# ------------------------------------------------------------
# Individual services (each needs `make db-up` first)
# ------------------------------------------------------------

api: ## Run only the Admin API (auto-reload)
	uv run uvicorn src.api.main:app --reload --port $(API_PORT)

user-ui: ## Run only the User UI (needs the API running)
	API_BASE_URL=http://localhost:$(API_PORT) uv run streamlit run src/ui/streamlit_app.py --server.port $(USER_UI_PORT)

admin-ui: ## Run only the Admin UI (needs the API running)
	API_BASE_URL=http://localhost:$(API_PORT) uv run streamlit run src/ui/admin_app.py --server.port $(ADMIN_UI_PORT)

# ------------------------------------------------------------
# Setup building blocks (used by `make setup`, runnable on their own)
# ------------------------------------------------------------

env: ## Create .env from .env.example and verify GOOGLE_API_KEY is set
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "📝 Created .env from .env.example."; \
		echo "   Set GOOGLE_API_KEY (https://aistudio.google.com/apikey), then run 'make setup' again."; \
		exit 1; \
	fi
	@if ! grep -qE '^GOOGLE_API_KEY=.+' .env; then \
		echo "❌ GOOGLE_API_KEY is empty in .env — set it, then re-run 'make setup'."; \
		exit 1; \
	fi
	@echo "✅ .env present and GOOGLE_API_KEY set."

install: ## Install Python dependencies (including dev) with uv
	uv sync --extra dev

ollama-check: ## Verify the Ollama daemon is up and the model is available
	@curl -fsS $(OLLAMA_URL)/api/tags >/dev/null 2>&1 || { \
		echo "❌ Ollama not reachable at $(OLLAMA_URL)."; \
		echo "   Start the Ollama app, then run: ollama signin"; \
		exit 1; \
	}
	@curl -fsS $(OLLAMA_URL)/api/tags | grep -q '"$(OLLAMA_MODEL)"' || { \
		echo "❌ Model '$(OLLAMA_MODEL)' not found."; \
		echo "   Run: ollama signin && ollama pull $(OLLAMA_MODEL)"; \
		exit 1; \
	}
	@echo "✅ Ollama ready ($(OLLAMA_MODEL))."

rag-index: ## Build & warm the RAG vector index
	uv run python scripts/build_rag_index.py

# ------------------------------------------------------------
# Databases
# ------------------------------------------------------------

db-up: ## Start Postgres + MongoDB (waits until healthy)
	docker compose up -d --wait

db-down: ## Stop the databases (keeps data)
	docker compose down

db-reset: ## Wipe DB volumes and re-seed from scratch
	docker compose down -v
	docker compose up -d --wait

db-logs: ## Tail database logs
	docker compose logs -f

# ------------------------------------------------------------
# Misc
# ------------------------------------------------------------

stop: db-down ## Stop the databases (alias for db-down)

test: ## Run the test suite
	uv run --env-file .env pytest tests/ -q

clean: ## Remove Python caches and test artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
	@echo "✅ Cleaned."
