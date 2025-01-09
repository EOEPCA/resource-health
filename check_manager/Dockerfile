FROM ghcr.io/astral-sh/uv:debian-slim

WORKDIR /app

COPY ./.python-version ./pyproject.toml ./uv.lock /app/
COPY ./src/ /app/src/

RUN uv python install && uv sync --frozen && uv pip install .
# Would like to compile to bytecode later on
# RUN uv sync --frozen --compile-bytecode

EXPOSE 8000
ENTRYPOINT ["uv", "run"]
CMD ["check-api-server-k8s"]