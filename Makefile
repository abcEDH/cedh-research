SHELL := /bin/sh

.PHONY: quickstart web-deps web-build web-dev web-start web-test web-test-contracts web-test-e2e backend-deps backend-ingest backend-help

quickstart:
	./scripts/quickstart.sh

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
