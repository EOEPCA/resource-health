import check_backends.k8s_backend.template_utils as tu

SOURCE = """
import requests

URL = environ["URL"]
COLLECTION_FIELD = environ["COLLECTION_FIELD"]
EXPECTED_COUNT = environ["EXPECTED_COUNT"]

def test_collections() -> None:
    response = requests.get(URL)
    assert response.ok
    resp_json = response.json()
    assert COLLECTION_FIELD in resp_json
    assert isinstance(resp_json[COLLECTION_FIELD], list)
    assert len(resp_json[COLLECTION_FIELD]) >= EXPECTED_COUNT
"""


class CollectionCheckArguments(tu.BaseModel):
    model_config = tu.ConfigDict(extra="forbid")
    url: str = tu.Field(json_schema_extra={"format": "textarea"})
    collection_field: str = tu.Field(
        description="Response field which has the collection to inspect"
    )
    expected_count: int = tu.Field(gt=0)


CollectionCheck = tu.simple_runner_template(
    template_id="collection_check",
    argument_type=CollectionCheckArguments,
    label="Collection Check Template",
    description="To create checks which query an endpoint and check that the returned collection size is not smaller than expected.",
    script_url=tu.src_to_data_url(SOURCE),
    runner_env=lambda template_args, userinfo: {
        "URL": template_args.url,
        "COLLECTION_FIELD": template_args.collection_field,
        "EXPECTED_COUNT": str(template_args.expected_count),
    },
    user_id=lambda template_args, userinfo: userinfo["username"],
    otlp_tls_secret="resource-health-healthchecks-certificate",
)