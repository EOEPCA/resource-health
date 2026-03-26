import check_backends.k8s_backend.template_utils as tu

# Parameterised health check script
CODE_SOURCE = """
from os import environ
import requests
from jsonpointer import resolve_pointer

URL = environ["URL"]
COLLECTION_POINTER = environ["COLLECTION_POINTER"]
EXPECTED_COUNT = int(environ["EXPECTED_COUNT"])


def test_collections() -> None:
    response = requests.get(URL)
    assert response.ok
    resp_json = response.json()
    collection = resolve_pointer(resp_json, COLLECTION_POINTER)
    assert isinstance(collection, list)
    assert len(collection) >= EXPECTED_COUNT
"""
# Additional Python libraries used by the script above
REQUIREMENTS_SOURCE = """
jsonpointer==3.0.0
"""


# Pydantic model from which the json schema for the health check template arguments is generated
# See https://docs.pydantic.dev/latest/concepts/json_schema/
class CollectionCheckArguments(tu.BaseModel):
    # Additional arguments besides `url`, `collection_pointer`, `expected_count` are
    # forbidden
    model_config = tu.ConfigDict(extra="forbid")

    url: str = tu.Field(json_schema_extra={"format": "textarea"})
    collection_pointer: str = tu.Field(
        description="Json pointer to the collection in the response to inspect",
        # Empty string is a valid json pointer. If this line is omitted, empty string will
        # be rejected by the health check website
        default="",
    )
    expected_count: int = tu.Field(gt=0)


CollectionCheck = tu.simple_runner_template(
    template_id="collection_check",
    argument_type=CollectionCheckArguments,
    label="Collection template",
    description="To create checks which query an endpoint and check that the returned collection size is not smaller than expected.",
    script_url=tu.src_to_data_url(CODE_SOURCE),
    requirements_url=tu.src_to_data_url(REQUIREMENTS_SOURCE),
    runner_env=lambda template_args, userinfo: {
        # Set URL, COLLECTION_POINTER, and EXPECTED_COUNT environment variables
        # to the values the user chooses when creating the check
        "URL": template_args.url,
        "COLLECTION_POINTER": template_args.collection_pointer,
        "EXPECTED_COUNT": str(template_args.expected_count),
    },
    user_id=lambda template_args, userinfo: userinfo["username"],
    otlp_tls_secret="resource-health-healthchecks-certificate",
)
