#!/bin/bash

# This structure is to ensure that $RH_RUNNER_RUN_AFTER is always executed at the end no matter what
# and that if any command fails (including the $RH_RUNNER_RUN_AFTER), the whole script also fails
(
    eval "$RH_RUNNER_RUN_BEFORE" || exit $?

    # Install requirements
    if [[ ! -z "$RH_RUNNER_REQUIREMENTS" ]]; then
        uv run upcat "$RH_RUNNER_REQUIREMENTS" > requirements.txt || exit $?
        uv pip install -r requirements.txt || exit $?
    fi

    uv run upcat "$RH_RUNNER_SCRIPT" > tests.py || exit $?

    # Run tests
    uv run opentelemetry-instrument --traces_exporter otlp --logs_exporter otlp "$@"
)
ret=$?
eval "$RH_RUNNER_RUN_AFTER" || ret=$?;
exit $ret
