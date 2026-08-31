FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY workspace.yaml ./

ENV PATH="/app/.venv/bin:$PATH" \
    DAGSTER_HOME=/app/dagster_home

RUN mkdir -p "$DAGSTER_HOME"
COPY dagster.yaml "$DAGSTER_HOME/dagster.yaml"
