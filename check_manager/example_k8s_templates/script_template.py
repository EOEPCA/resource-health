import check_backends.k8s_backend.template_utils as tu


class ScriptTemplateArguments(tu.BaseModel):
    model_config = tu.ConfigDict(extra="forbid")
    script: str = tu.Field(json_schema_extra={"format": "textarea"})
    requirements: str = tu.Field(json_schema_extra={"format": "textarea"}, default="")


GenericScriptTemplate = tu.simple_runner_template(
    template_id="generic_script_template",
    argument_type=ScriptTemplateArguments,
    label="Generic script template",
    description="Runs a user-provided pytest script from a specified remote or data url",
    script_url=lambda template_args, userinfo: template_args.script,
    requirements_url=lambda template_args, userinfo: template_args.requirements,
    user_id=lambda template_args, userinfo: userinfo["username"],
    otlp_tls_secret="resource-health-healthchecks-certificate",
)
