FROM python:3.11-slim AS compiler
ENV PYTHONUNBUFFERED=1

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY ./utilities /utilities
COPY ./runner-image/base_requirements.txt /requirements.txt
RUN pip install -Ur /requirements.txt

FROM python:3.11-slim AS runner

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    wget && \
    # Clean up after installation
    apt-get clean && rm -rf /var/lib/apt-get/lists/*

COPY --from=compiler /venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /app

COPY ./runner-image/run_script.sh /app/
COPY ./runner-image/tests.py /app/

## Replace with a (preinstalled) set of packages
COPY ./instrumentation/conftest.py /app/

RUN chmod +x /app/run_script.sh

ENTRYPOINT [ "/app/run_script.sh" ]

CMD [ "pytest", "--export-traces", "tests.py" ]
