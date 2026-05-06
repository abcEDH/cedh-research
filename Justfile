set shell := ["bash", "-cu"]

quickstart:
    ./scripts/quickstart.sh

quickstart-no-backend:
    ./scripts/quickstart.sh --no-backend

# Web targets
web-deps:
	npm ci --prefix apps/web

web-build:
	npm run web:build

web-dev:
	npm run web:dev

web-start:
	npm run web:start

web-test:
	npm run web:test

web-test-contracts:
	npm run web:test:contracts

web-test-e2e:
	npm run web:test:e2e

verify-frontend:
	npm run verify:frontend

preview-deploy-frontend:
	npm run preview:frontend

# Backend targets
backend-deps:
	python -m pip install -r packages/backend/requirements.txt

backend-ingest:
	python packages/backend/src/ingest.py

backend-help:
	python packages/backend/src/ingest.py --help

# Dev/CI targets
check:
	@echo "Running all checks..."
	npm run docs:hygiene
	npm run docs:check
	npm run web:lint
	npm run web:test:ci
	@if command -v ruff >/dev/null; then \
		ruff check packages/backend/src; \
	else \
		echo "Skipping ruff (not installed)"; \
	fi
	@if command -v mypy >/dev/null; then \
		mypy packages/backend/src; \
	else \
		echo "Skipping mypy (not installed)"; \
	fi
	PYTHONPATH=packages/backend/src python3 -m unittest discover packages/backend/tests
