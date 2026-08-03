SHELL := /bin/bash
.DEFAULT_GOAL := help
PNPM := ./scripts/pnpm
UV := ./scripts/uv

.PHONY: help runtime setup dirs hooks doctor dev demo demo-video api web migrate contracts lint typecheck test build e2e release-check verify clean

help:
	@echo "ReplayTutor local development"
	@echo "  make setup      Install locked dependencies, create runtime dirs, migrate DB, install hooks"
	@echo "  make dev        Start Vite (:5173) and FastAPI (:8788)"
	@echo "  make doctor     Check dependencies, ports, and local runtime paths"
	@echo "  make demo       Start an isolated demo with the bundled BTCUSDT snapshot"
	@echo "  make demo-video Record and render the bilingual Remotion demo"
	@echo "  make e2e        Run isolated browser tests (requires Playwright Chromium)"
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

doctor:
	/bin/bash scripts/doctor.sh

dev: runtime dirs
	/bin/bash scripts/dev-preflight.sh 5173 8788
	$(PNPM) dev

demo: runtime
	REPLAYTUTOR_DATA_DIR=data/demo /bin/bash scripts/demo-prepare.sh
	REPLAYTUTOR_DATA_DIR=data/demo REPLAYTUTOR_PORT=8790 REPLAYTUTOR_CORS_ORIGINS=http://127.0.0.1:5174 VITE_API_BASE_URL=http://127.0.0.1:8790 $(PNPM) exec concurrently --kill-others --success first --names web,api --prefix-colors cyan,magenta "$(PNPM) --filter @replaytutor/web exec vite --host 127.0.0.1 --port 5174 --strictPort" "$(UV) run --project apps/api replaytutor api"

demo-video:
	$(PNPM) demo:record -- --locale en-US
	$(PNPM) demo:record -- --locale zh-CN
	$(PNPM) demo:render
	$(PNPM) demo:verify

api: runtime dirs
	$(PNPM) api

web: runtime
	$(PNPM) web

migrate: dirs
	$(UV) run --project apps/api python -c "from replaytutor.config import get_settings; from replaytutor.storage.database import upgrade_database; upgrade_database(get_settings())"

contracts:
	$(PNPM) contracts

lint:
	$(PNPM) lint
	$(UV) run --project apps/api ruff check --config apps/api/pyproject.toml apps/api tests/backend tests/e2e scripts

typecheck:
	$(PNPM) typecheck
	$(UV) run --project apps/api pyright apps/api/replaytutor tests/backend scripts

test:
	/bin/bash tests/infrastructure/test-runtime-bootstrap.sh
	/bin/bash tests/infrastructure/test-migrate-config.sh
	$(PNPM) test
	$(UV) run --project apps/api pytest tests/backend

build:
	$(PNPM) build
	$(UV) run --project apps/api python -c "import replaytutor.main"

release-check: build
	$(PNPM) demo:verify
	/bin/bash scripts/check-release-artifacts.sh

e2e:
	mkdir -p test-results
	$(UV) run --project apps/api pytest -q tests/e2e

verify: contracts lint typecheck test release-check

clean:
	rm -rf apps/web/dist apps/web/.vite apps/demo-video/out apps/demo-video/.remotion packages/contracts/dist coverage playwright-report test-results
	rm -f apps/web/*.tsbuildinfo
	rm -rf apps/api/.pytest_cache apps/api/.ruff_cache apps/api/.mypy_cache apps/api/.pyright
