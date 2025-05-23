from pydantic import ConfigDict
from check_backends.k8s_backend.template_utils import *
from typing import TypedDict

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


class SimplePingArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint: str = Field(json_schema_extra={"format": "textarea"})
    expected_status_code: int = Field(ge=100, lt=600, default=200)


SimplePing = simple_runner_template(
    template_id="simple_ping",
    argument_type=SimplePingArguments,
    label="Simple ping template",
    description="Simple template with preset script for pinging single endpoint.",
    script_url=src_to_data_url(SIMPLE_PING_SRC),
    runner_env=lambda template_args, userinfo: {
        "GENERIC_ENDPOINT": template_args.endpoint,
        "EXPECTED_STATUS_CODE": str(template_args.expected_status_code),
    },
    user_id=lambda template_args, userinfo: userinfo["username"],
    otlp_tls_secret="resource-health-healthchecks-certificate",
)
