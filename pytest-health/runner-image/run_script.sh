#!/bin/bash

# Install requirements
if [[ ! -z "$RESOURCE_HEALTH_RUNNER_REQUIREMENTS" ]]; then
    uv run upcat "$RESOURCE_HEALTH_RUNNER_REQUIREMENTS" > requirements.txt
	uv pip install -r requirements.txt
fi

uv run upcat "$RESOURCE_HEALTH_RUNNER_SCRIPT" > tests.py

# Run tests
uv run opentelemetry-instrument --traces_exporter otlp --logs_exporter otlp "$@"

