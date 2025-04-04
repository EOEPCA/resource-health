from check_backends.k8s_backend.template_utils import *


class SimplePingArguments(BaseModel):
    endpoint: str = Field(json_schema_extra={"format": "textarea"})
    expected_status_code: int = Field(ge=100, lt=600, default=200)


# def simple_ping_annotations(self, template_args : SimplePingArguments) -> dict[str, Any]:
#     return {}

SIMPLE_PING_SRC = """from os import environ
import requests

GENERIC_ENDPOINT: str = environ["GENERIC_ENDPOINT"]
EXPECTED_STATUS_CODE: int = int(environ["EXPECTED_STATUS_CODE"])


def test_ping() -> None:
    response = requests.get(
        GENERIC_ENDPOINT,
    )
    assert response.status_code == EXPECTED_STATUS_CODE
"""


def simple_ping_containers(template_args: SimplePingArguments) -> list[Container]:
    return [
        runner_container(
            # "data:text/plain;base64,ZnJvbS...QVRVU19DT0RFCg=="
            script_url=src_to_data_url(SIMPLE_PING_SRC),
            env={
                "GENERIC_ENDPOINT": template_args.endpoint,
                "EXPECTED_STATUS_CODE": str(template_args.expected_status_code),
            },
        )
    ]


SimplePing = cronjob_template(
    template_id="simple_ping",
    argument_type=SimplePingArguments,
    label="Simple ping template",
    description="Simple template with preset script for pinging single endpoint.",
    # annotations = simple_ping_annotations,
    containers=simple_ping_containers,
)
