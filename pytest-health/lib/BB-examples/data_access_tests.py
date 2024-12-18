from os import environ
import requests

DATA_ACCESS_HOST: str = environ["DATA_ACCESS_HOST"]


def test_ping_raster_api() -> None:
    response = requests.get(
        f"{DATA_ACCESS_HOST}/raster/healthz",
    )
    assert response.status_code == 200


def test_ping_vector_api() -> None:
    response = requests.get(
        f"{DATA_ACCESS_HOST}/vector/healthz",
    )
    assert response.status_code == 200


def test_ping_stac_api() -> None:
    response = requests.get(
        f"{DATA_ACCESS_HOST}/stac/_mgmt/ping",
    )
    assert response.status_code == 200
