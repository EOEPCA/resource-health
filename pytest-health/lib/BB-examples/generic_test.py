from os import environ
import requests

GENERIC_ENDPOINT: str = environ["GENERIC_ENDPOINT"]
EXPECTED_STATUS_CODE: int = int(environ["EXPECTED_STATUS_CODE"])


def test_ping() -> None:
    response = requests.get(
        GENERIC_ENDPOINT,
    )
    assert response.status_code == EXPECTED_STATUS_CODE
