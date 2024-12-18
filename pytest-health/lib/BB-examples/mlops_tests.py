from os import environ
import requests

SHARING_HUB_HOST: str = environ["SHARING_HUB_HOST"]
MFLOW_SHARING_HUB_HOST: str = environ["MFLOW_SHARING_HUB_HOST"]


def test_ping_sharing_hub() -> None:
    response = requests.get(
        f"{SHARING_HUB_HOST}/status",
    )
    assert response.status_code == 200


def test_ping_mlflow_sharing_hub() -> None:
    response = requests.get(
        f"{MFLOW_SHARING_HUB_HOST}/mlflow/health",
    )
    assert response.status_code == 200
