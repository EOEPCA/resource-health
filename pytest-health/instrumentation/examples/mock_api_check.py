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

def test_dice_sum() -> None:
    r = requests.get(MOCK_API_HOST)
    assert int(r.content) <= 7

def test_ping_api() -> None:
    r = requests.get(MOCK_API_HOST)
    assert r.status_code == 200
