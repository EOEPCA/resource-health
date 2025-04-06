FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS build

WORKDIR /app

COPY ./.python-version ./pyproject.toml ./uv.lock /app/
COPY ./src/ /app/src/

RUN uv sync --python-preference only-system --no-dev --frozen --compile-bytecode --no-editable

FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

COPY --from=build /app/.venv /app/.venv
COPY ./example_k8s_templates/ping_template.py /app/templates/ping_template.py
COPY ./example_hooks/basic_http_hooks/hooks.py /app/hooks/

EXPOSE 8000
ENTRYPOINT [".venv/bin/check-api-server-k8s"]
