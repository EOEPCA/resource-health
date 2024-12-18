from os import environ
import requests

OPEN_ID_CONFIGURATION_HOST: str = environ["OPEN_ID_CONFIGURATION_HOST"]
OPA_ENDPOINT: str = environ["OPA_ENDPOINT"]
IDENTITY_API_ENDPOINT: str = environ["IDENTITY_API_ENDPOINT"]


def test_ping_openid_configuration() -> None:
    response = requests.get(
        f"{OPEN_ID_CONFIGURATION_HOST}/openid-configuration",
    )
    assert response.status_code == 200


def test_ping_opa() -> None:
    response = requests.get(
        OPA_ENDPOINT,
    )
    assert response.status_code == 200


def test_ping_identity_api() -> None:
    response = requests.get(
        IDENTITY_API_ENDPOINT,
    )
    assert response.status_code == 200
