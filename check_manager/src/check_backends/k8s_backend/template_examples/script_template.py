from typing import override
from pydantic import TypeAdapter
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_env_var import V1EnvVar

from api_utils.json_api_types import Json
from check_backends.check_backend import (
    CheckTemplate,
    CheckTemplateAttributes,
    CheckTemplateId,
    CheckTemplateMetadata,
    CronExpression,
)
from check_backends.k8s_backend.template_utils import make_base_cronjob
from check_backends.k8s_backend.templates import CronjobTemplate


class DefaultK8sTemplate(CronjobTemplate):
    @override
    def get_check_template(self) -> CheckTemplate:
        return CheckTemplate(
            id=CheckTemplateId("default_k8s_template"),
            attributes=CheckTemplateAttributes(
                metadata=CheckTemplateMetadata(
                    label="Default Kubernetes template",
                    description="Default template for checks in the Kubernetes backend.",
                ),
                arguments={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "object",
                    "properties": {
                        "health_check.name": {
                            "type": "string",
                        },
                        "script": {"type": "string", "format": "textarea"},
                        "requirements": {"type": "string", "format": "textarea"},
                    },
                    "required": [
                        "health_check.name",
                        "script",
                    ],
                },
            ),
        )

    @override
    def make_cronjob(
        self,
        template_args: Json,
        schedule: CronExpression,
    ) -> V1CronJob:
        health_check_name = TypeAdapter(str).validate_python(
            template_args["health_check.name"]
        )
        script = TypeAdapter(str).validate_python(template_args["script"])
        requirements: str | None = TypeAdapter(str | None).validate_python(
            template_args.get("requirements")
        )
        cronjob = make_base_cronjob(
            schedule=schedule,
            health_check_name=health_check_name,
        )
        env = cronjob.spec.job_template.spec.template.spec.containers[0].env or []
        if script:
            env.append(
                V1EnvVar(
                    name="RESOURCE_HEALTH_RUNNER_SCRIPT",
                    value=script,
                )
            )
        if requirements:
            env.append(
                V1EnvVar(
                    name="RESOURCE_HEALTH_RUNNER_REQUIREMENTS",
                    value=requirements,
                )
            )
        cronjob.spec.job_template.spec.template.spec.containers[0].env = env
        return cronjob
