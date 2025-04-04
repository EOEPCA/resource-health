FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS compiler

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ./utilities /app/utilities
COPY ./runner-image/base_requirements.txt /app/requirements.txt

RUN uv venv && uv pip install -Ur requirements.txt

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runner

COPY --from=compiler /app/.venv /app/.venv

WORKDIR /app

## TODO: Replace conftest with a (preinstalled) package
COPY ./runner-image/run_script.sh ./runner-image/tests.py ./instrumentation/conftest.py /app/

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl git && \
    # Clean up after installation
    apt-get clean && rm -rf /var/lib/apt-get/lists/* && \
    chmod +x /app/run_script.sh

ENTRYPOINT [ "/app/run_script.sh" ]

CMD [ "pytest", "--export-traces", "tests.py" ]
