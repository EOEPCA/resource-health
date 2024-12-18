from os import environ
import requests

WORKSPACE_HOST: str = environ["WORKSPACE_TEST_HOST"]


def test_ping_workspace_api() -> None:
    response = requests.get(
        f"{WORKSPACE_HOST}/probe",
    )
    assert response.status_code == 200


def test_ping_prometheus() -> None:
    response = requests.get(
        f"{WORKSPACE_HOST}/metrics",
    )
    assert response.status_code == 200
