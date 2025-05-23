import check_backends.k8s_backend.template_utils as tu
import os


class TelemetryAccessArguments(tu.BaseModel):
    model_config = tu.ConfigDict(extra="forbid")
    script: str = tu.Field(json_schema_extra={"format": "textarea"})
    requirements: str = tu.Field(json_schema_extra={"format": "textarea"}, default="")


TelemetryAccessTemplate = tu.simple_runner_template(
    template_id="telemetry_access_template",
    argument_type=TelemetryAccessArguments,
    label="Script with telemetry access",
    description="Health check template that runs a userscript with telemetry access on localhost:8080",
    script_url=lambda template_args, userinfo: template_args.script,
    requirements_url=lambda template_args, userinfo: template_args.requirements,
    user_id=lambda template_args, userinfo: userinfo["username"],
    otlp_tls_secret="resource-health-healthchecks-certificate",
    proxy=True,
    proxy_oidc_client_secret=(
        "resource-health-iam-client-credentials",
        "client_id",
        "client_secret",
    ),
    proxy_oidc_refresh_token_secret=lambda template_args, userinfo: (
        f"resource-health-{userinfo['username']}-offline-secret",
        "offline_token",
    ),
    proxy_oidc_url=os.environ.get("OPEN_ID_CONNECT_URL"),
)
