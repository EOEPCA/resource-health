FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS build

WORKDIR /app

COPY ./.python-version ./pyproject.toml ./uv.lock ./README.md /app/
COPY ./src/ /app/src/

RUN uv sync --python-preference only-system --no-dev --frozen --compile-bytecode --no-editable

FROM python:3.13-slim-bookworm AS runner

WORKDIR /app

COPY --from=build /app/.venv /app/.venv

EXPOSE 50051
ENTRYPOINT [".venv/bin/trace_receiver", "&", ".venv/bin/notifier"]
