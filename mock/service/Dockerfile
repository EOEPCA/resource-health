FROM python:3.11-slim as compiler
ENV PYTHONUNBUFFERED 1

WORKDIR /app/

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY ./requirements.txt /app/requirements.txt
RUN pip install -Ur requirements.txt

FROM python:3.11-slim as runner
WORKDIR /app/
COPY --from=compiler /venv /venv

ENV PATH="/venv/bin:$PATH"
COPY app.py /app/app.py
CMD [ "opentelemetry-instrument", "--traces_exporter", "otlp", "--logs_exporter", "otlp", "flask", "--app", "app.py", "run", "--host", "0.0.0.0" ]
