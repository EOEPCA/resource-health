from os import environ
import requests

RESOURCE_CATALOGUE_ENDPOINT: str = environ["RESOURCE_CATALOGUE_ENDPOINT"]


def test_ping_resource_catalogue() -> None:
    response = requests.get(
        RESOURCE_CATALOGUE_ENDPOINT,
    )
    assert response.status_code == 200
