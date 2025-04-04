from check_backends.k8s_backend.template_utils import *


class DefaultK8sArguments(BaseModel):
    script: str = Field(json_schema_extra={"format": "textarea"})
    requirements: str = Field(json_schema_extra={"format": "textarea"}, default="")


def default_k8s_template_containers(
    template_args: DefaultK8sArguments,
) -> list[Container]:
    return [
        runner_container(
            script_url=template_args.script, requirements_url=template_args.requirements
        )
    ]


DefaultK8sTemplate = cronjob_template(
    template_id="default_k8s_template",
    argument_type=DefaultK8sArguments,
    label="Default Kubernetes template",
    description="Default template for checks in the Kubernetes backend.",
    # annotations = simple_ping_annotations,
    containers=default_k8s_template_containers,
)
