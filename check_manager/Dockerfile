FROM ghcr.io/astral-sh/uv:python3.12-bookworm as build

WORKDIR /app

COPY ./.python-version ./pyproject.toml ./uv.lock /app/
COPY ./src/ /app/src/

RUN uv sync --python-preference only-system --no-dev --frozen --compile-bytecode --no-editable

FROM python:3.12-slim-bookworm as runner

WORKDIR /app

COPY --from=build /app/.venv /app/.venv
COPY ./templates/ /app/templates/

EXPOSE 8000
ENTRYPOINT [".venv/bin/check-api-server-k8s"]
