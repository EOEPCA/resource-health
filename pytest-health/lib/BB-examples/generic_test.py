from os import environ
import requests

GENERIC_ENDPOINT: str = environ["GENERIC_ENDPOINT"]


def test_ping() -> None:
    response = requests.get(
        GENERIC_ENDPOINT,
    )
    assert response.status_code == 200
