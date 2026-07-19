SHELL := /bin/bash
.DEFAULT_GOAL := help
PNPM := ./scripts/pnpm
UV := ./scripts/uv

.PHONY: help runtime setup dirs hooks dev api web migrate contracts lint typecheck test build verify clean

help:
	@echo "ReplayTutor local development"
	@echo "  make setup      Install locked dependencies, create runtime dirs, migrate DB, install hooks"
	@echo "  make dev        Start Vite (:5173) and FastAPI (:8788)"
	@echo "  make verify     Contract, lint, type, test, and build gate"

runtime:
	@$(PNPM) --version
	@$(UV) --version

setup: runtime dirs
	$(PNPM) install --frozen-lockfile
	$(UV) sync --project apps/api --frozen
	$(MAKE) migrate
	$(MAKE) hooks

dirs:
	mkdir -p data/market/snapshots data/imports data/runtime/agent-runs data/exports logs

hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-push

dev: runtime dirs
	$(PNPM) dev

api: runtime dirs
	$(PNPM) api

web: runtime
	$(PNPM) web

migrate: dirs
	$(UV) run --project apps/api alembic -c apps/api/alembic.ini upgrade head

contracts:
	$(PNPM) contracts

lint:
	$(PNPM) lint
	$(UV) run --project apps/api ruff check apps/api tests/backend scripts

typecheck:
	$(PNPM) typecheck
	$(UV) run --project apps/api pyright apps/api/replaytutor tests/backend scripts

test:
	/bin/bash tests/infrastructure/test-runtime-bootstrap.sh
	$(PNPM) test
	$(UV) run --project apps/api pytest tests/backend

build:
	$(PNPM) build
	$(UV) run --project apps/api python -c "import replaytutor.main"

verify: contracts lint typecheck test build

clean:
	rm -rf apps/web/dist apps/web/.vite packages/contracts/dist coverage playwright-report test-results
	rm -f apps/web/*.tsbuildinfo
	rm -rf apps/api/.pytest_cache apps/api/.ruff_cache apps/api/.mypy_cache apps/api/.pyright
