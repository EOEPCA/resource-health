from check_backends.k8s_backend.template_utils import *
import os

class TelemetryAccessArguments(BaseModel):
    script: str = Field(json_schema_extra={"format": "textarea"})
    requirements: str = Field(json_schema_extra={"format": "textarea"}, default="")


def telemetry_access_template_containers(
    template_args: TelemetryAccessArguments,
    userinfo: Any,
) -> list[Container]:
    assert isinstance(userinfo, dict)

    return [
        runner_container(
            script_url=template_args.script,
            requirements_url=template_args.requirements,
            ## Without native sidecar containers (only available in recent k8S as beta, we need to explicitly kill the proxy)
            ## which is what the /killkillkill call does
            args=["-c", "/app/run_script.sh pytest --export-traces -rP --suppress-tests-failed-exit-code tests.py; ret=$?; curl -s 'http://127.0.0.1:8080/quitquitquit'; exit $ret"],
            resource_attributes={
                'user.id': userinfo['username'],
            }
        ),
        oidc_mitmproxy_container(
            remote_domain="https://opensearch-cluster-master-headless:9200",
            openid_connect_url=os.environ["OPEN_ID_CONNECT_URL"],
            openid_client_id_secret=("resource-health-iam-client-credentials", "client_id"),
            openid_client_secret_secret=("resource-health-iam-client-credentials", "client_secret"),
            refresh_token_secret=(f"resource-health-{userinfo['username']}-offline-secret", "offline_token")
        )
    ]


TelemetryAccessTemplate = cronjob_template(
    template_id="telemetry_access_template",
    argument_type=TelemetryAccessArguments,
    label="Script with telemetry access",
    description="Health check template that runs a userscript with telemetry access on localhost:8080",
    # annotations = telemetry_access_template_annotations,
    containers=telemetry_access_template_containers,
    # volumes = telemetry_access_template_volumes,
)
