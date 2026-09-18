FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY packages/backend/pyproject.toml packages/backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY packages/backend/src ./src
COPY packages/backend/data ./data

ENTRYPOINT ["uv", "run", "--no-sync", "python", "src/prefect_flows.py"]
