.DEFAULT_GOAL := help
SHELL := /bin/bash
PYTHON ?= python3

API_PY    := api/.venv/bin/python
VISION_PY := vision/.venv/bin/python

.PHONY: help env install up down restart ps logs health cameras lint fmt test test-integration clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

env: ## Create .env with random passwords (keeps an existing .env)
	@$(PYTHON) scripts/make_env.py

install: ## Create virtualenvs for api and vision with dev tools
	cd api && $(PYTHON) -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -e '.[dev]'
	cd vision && $(PYTHON) -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -e '.[dev]'

up: env ## Start the infrastructure stack
	docker compose up -d --build --wait

down: ## Stop the stack (data volumes are kept)
	docker compose down

restart: down up ## Restart the stack

ps: ## Show service status
	docker compose ps

logs: ## Follow logs (make logs s=mediamtx for one service)
	docker compose logs -f $(s)

health: ## Check API readiness (postgres, redis, minio)
	@curl -s localhost:$${API_PORT:-8000}/health/ready | $(PYTHON) -m json.tool

cameras: ## Connect to every camera and report resolution / fps
	cd vision && .venv/bin/python -m anpr.tools.check_cameras

lint: ## Lint and check formatting
	$(API_PY) -m ruff check . && $(API_PY) -m ruff format --check .

fmt: ## Auto-format and fix lint issues
	$(API_PY) -m ruff check --fix . && $(API_PY) -m ruff format .

test: ## Unit tests
	cd api && .venv/bin/python -m pytest -q
	cd vision && .venv/bin/python -m pytest -q

test-integration: ## Integration tests against the running stack
	cd api && INTEGRATION=1 .venv/bin/python -m pytest -q -m integration

clean: ## Stop the stack AND delete all data volumes
	docker compose down -v
