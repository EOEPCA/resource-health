#!/bin/bash

cd /app

## TODO: Make optional by adding a default

# Install requirements
if [[ ! -z "$RESOURCE_HEALTH_RUNNER_REQUIREMENTS" ]]; then
	pip3 install -r <(ucat "$RESOURCE_HEALTH_RUNNER_REQUIREMENTS")
fi

# Run tests
opentelemetry-instrument --traces_exporter otlp --logs_exporter otlp "$@"

