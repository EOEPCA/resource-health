from pydantic import ConfigDict
from check_backends.k8s_backend.template_utils import *


class DefaultK8sArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    script: str = Field(json_schema_extra={"format": "textarea"})
    requirements: str = Field(json_schema_extra={"format": "textarea"}, default="")


GenericScriptTemplate = simple_runner_template(
    template_id="generic_script_template",
    argument_type=DefaultK8sArguments,
    label="Generic script template",
    description="Runs a user-provided pytest script from a specified remote or data url",
    script_url=lambda template_args, userinfo: template_args.script,
    requirements_url=lambda template_args, userinfo: template_args.requirements,
    user_id=lambda template_args, userinfo: userinfo["username"],
    otlp_tls_secret="resource-health-healthchecks-certificate",
)
