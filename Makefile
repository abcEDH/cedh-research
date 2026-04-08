SHELL := /bin/sh

.PHONY: web-deps web-build web-dev web-start web-test web-test-contracts web-test-e2e backend-deps backend-ingest backend-help

web-deps:
	npm ci --prefix apps/web

web-build:
	npm run --prefix apps/web build

web-dev:
	npm run --prefix apps/web dev

web-start:
	npm run --prefix apps/web start

web-test:
	npm run --prefix apps/web test

web-test-contracts:
	npm run --prefix apps/web test:contracts

web-test-e2e:
	npm run --prefix apps/web test:e2e

backend-deps:
	python -m pip install -r packages/backend/requirements.txt

backend-ingest:
	python packages/backend/src/ingest.py

backend-help:
	python packages/backend/src/ingest.py --help

check:
	@echo "Running all checks..."
	npm run docs:hygiene
	npm run docs:check
	npm --workspace apps/web run lint
	npm --workspace apps/web run test:ci
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
