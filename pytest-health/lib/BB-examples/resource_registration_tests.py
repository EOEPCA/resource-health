from os import environ
import requests

HARVESTER_WORKFLOW_ENGINE_HOST: str = environ["HARVESTER_WORKFLOW_ENGINE_HOST"]
HARVESTER_WORKFLOW_ENGINE_USERNAME: str = environ["HARVESTER_WORKFLOW_ENGINE_USERNAME"]
HARVESTER_WORKFLOW_ENGINE_PASSWORD: str = environ["HARVESTER_WORKFLOW_ENGINE_PASSWORD"]
REGISTRATION_API_ENDPOINT: str = environ["REGISTRATION_API_ENDPOINT"]


def test_ping_harvester_workflow_engine() -> None:
    response = requests.get(
        f"{HARVESTER_WORKFLOW_ENGINE_HOST}/flowable-rest/actuator/health",
        auth=(HARVESTER_WORKFLOW_ENGINE_USERNAME, HARVESTER_WORKFLOW_ENGINE_PASSWORD),
    )
    assert response.status_code == 200


def test_ping_registration_api() -> None:
    response = requests.get(
        REGISTRATION_API_ENDPOINT,
    )
    assert response.status_code == 200
