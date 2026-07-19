SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help setup dirs hooks dev api web migrate contracts lint typecheck test build verify clean

help:
	@echo "ReplayTutor local development"
	@echo "  make setup      Install locked dependencies, create runtime dirs, migrate DB, install hooks"
	@echo "  make dev        Start Vite (:5173) and FastAPI (:8788)"
	@echo "  make verify     Contract, lint, type, test, and build gate"

setup: dirs
	pnpm install --frozen-lockfile
	uv sync --project apps/api --frozen
	$(MAKE) migrate
	$(MAKE) hooks

dirs:
	mkdir -p data/market/snapshots data/imports data/runtime/agent-runs data/exports logs

hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-push

dev: dirs
	pnpm dev

api: dirs
	pnpm api

web:
	pnpm web

migrate: dirs
	uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head

contracts:
	pnpm contracts

lint:
	pnpm lint
	uv run --project apps/api ruff check apps/api tests/backend scripts

typecheck:
	pnpm typecheck
	uv run --project apps/api pyright apps/api/replaytutor tests/backend scripts

test:
	pnpm test
	uv run --project apps/api pytest tests/backend

build:
	pnpm build
	uv run --project apps/api python -c "import replaytutor.main"

verify: contracts lint typecheck test build

clean:
	rm -rf apps/web/dist apps/web/.vite packages/contracts/dist coverage playwright-report test-results
	rm -f apps/web/*.tsbuildinfo
	rm -rf apps/api/.pytest_cache apps/api/.ruff_cache apps/api/.mypy_cache apps/api/.pyright
