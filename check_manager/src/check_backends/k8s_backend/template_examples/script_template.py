from check_backends.k8s_backend.template_utils import *

class DefaultK8sArguments(BaseModel):
    script : str = Field(json_schema_extra={'format':'textarea'})
    requirements : str|None = Field(json_schema_extra={'format':'textarea'}, default=None)

def default_k8s_template_containers(template_args : DefaultK8sArguments) -> list[Container]:
    env = {
        "RESOURCE_HEALTH_RUNNER_SCRIPT": template_args.script
    }

    if template_args.requirements is not None:
        env["RESOURCE_HEALTH_RUNNER_REQUIREMENTS"] = template_args.requirements
    
    return [
        container(
            image=DEFAULT_CONTAINER_IMAGE,
            env=env
        )
    ]

DefaultK8sTemplate = cronjob_template(
    template_id = "default_k8s_template",
    argument_type = DefaultK8sArguments,
    label="Default Kubernetes template",
    description="Default template for checks in the Kubernetes backend.",
    # annotations = simple_ping_annotations,
    containers = default_k8s_template_containers,
)
