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
from check_backends.k8s_backend.template_utils import (
    make_base_cronjob,
    make_sidecar_container,
)
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
                        "script": {"type": "string", "format": "textarea"},
                        "requirements": {"type": "string", "format": "textarea"},
                    },
                    "required": [
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
        username: str,
    ) -> V1CronJob:
        script = TypeAdapter(str).validate_python(template_args["script"])
        requirements: str | None = TypeAdapter(str | None).validate_python(
            template_args.get("requirements")
        )
        cronjob = make_base_cronjob(
            schedule=schedule,
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
        cronjob.spec.job_template.spec.template.spec.containers[0].command = [
            "/usr/bin/bash",
        ]
        cronjob.spec.job_template.spec.template.spec.containers[0].args = [
            "-c",
            (
                "/app/run_script.sh pytest --export-traces -rP "
                "--suppress-tests-failed-exit-code tests.py "
                f"--user-id {username}; ret=$?; "
                "curl -s 'http://127.0.0.1:8080/quitquitquit'; "
                "exit $ret"
            ),
        ]
        cronjob.spec.job_template.spec.template.spec.containers.append(
            make_sidecar_container(username),
        )

        return cronjob
