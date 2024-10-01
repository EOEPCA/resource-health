import os

import requests

## TODO: Use OpenTelemetry agent automated instrumentation instead
from opentelemetry.instrumentation.requests import RequestsInstrumentor
RequestsInstrumentor().instrument()

MOCK_API_HOST = (
    os.environ["MOCK_API_HOST"]
    if "MOCK_API_HOST" in os.environ
    else "http://127.0.0.1:5000"
)


def test_api() -> None:
    r = requests.get(MOCK_API_HOST)
    assert r.content == b"Hello!"


def test_which_will_fail() -> None:
    assert 2 == 3


def test_which_wont_fail() -> None:
    assert 3 == 3
