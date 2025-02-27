import json
from kubernetes_asyncio.client.models.v1_container import V1Container
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_cron_job_spec import V1CronJobSpec
from kubernetes_asyncio.client.models.v1_env_var import V1EnvVar
from kubernetes_asyncio.client.models.v1_job_spec import V1JobSpec
from kubernetes_asyncio.client.models.v1_pod_spec import V1PodSpec
from kubernetes_asyncio.client.models.v1_job_template_spec import V1JobTemplateSpec
from kubernetes_asyncio.client.models.v1_pod_template_spec import V1PodTemplateSpec
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from pydantic import TypeAdapter
from typing import Optional, override

from api_interface import (
    Json,
)
from check_backends.k8s_backend.templates import (
    CronjobTemplate,
    CheckTemplate,
    CheckTemplateId,
    CronExpression,
)

CONTAINER_IMAGE: str = "docker.io/eoepca/healthcheck_runner:2.0.0-beta2"


def make_base_cronjob(
    schedule: Optional[CronExpression] = None,
    health_check_name: Optional[str] = None,
) -> V1CronJob:
    cronjob = V1CronJob(
        api_version="batch/v1",
        kind="CronJob",
        metadata=V1ObjectMeta(
            annotations={
                "health_check_label": health_check_name,
            },
        ),
        spec=V1CronJobSpec(
            schedule=schedule,
            job_template=V1JobTemplateSpec(
                spec=V1JobSpec(
                    template=V1PodTemplateSpec(
                        spec=V1PodSpec(
                            containers=[
                                V1Container(
                                    name="healthcheck",
                                    image=CONTAINER_IMAGE,
                                    image_pull_policy="IfNotPresent",
                                ),
                            ],
                            restart_policy="OnFailure",
                        ),
                    ),
                ),
            ),
        ),
    )
    if schedule:
        cronjob.spec.schedule = schedule
    return cronjob


class DefaultK8sTemplate(CronjobTemplate):
    @override
    def get_check_template(self) -> CheckTemplate:
        return CheckTemplate(
            id=CheckTemplateId("default_k8s_template"),
            metadata={
                "label": "Default Kubernetes template",
                "description": "Default template for checks in the Kubernetes backend.",
            },
            arguments={
                "$schema": "http://json-schema.org/draft-07/schema",
                "type": "object",
                "properties": {
                    "health_check.name": {
                        "type": "string",
                    },
                    "script": {
                        "type": "string",
                        "format": "textarea"
                    },
                    "requirements": {
                        "type": "string",
                        "format": "textarea"
                    },
                },
                "required": [
                    "health_check.name",
                    "script",
                ],
            },
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


class SimplePing(CronjobTemplate):
    @override
    def get_check_template(self) -> CheckTemplate:
        return CheckTemplate(
            id=CheckTemplateId("simple_ping"),
            metadata={
                "label": "Simple ping template",
                "description": "Simple template with preset script for pinging single endpoint.",
            },
            arguments={
                "$schema": "http://json-schema.org/draft-07/schema",
                "type": "object",
                "properties": {
                    "health_check.name": {
                        "type": "string",
                    },
                    "endpoint": {
                        "type": "string",
                        "format": "textarea",
                    },
                    "expected_status_code": {
                        "type": "integer",
                        "minimum": 100,
                        "exclusiveMaximum": 600,
                        "default": 200,
                    },
                },
                "required": [
                    "health_check.name",
                    "endpoint",
                ],
            },
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
        endpoint = TypeAdapter(str).validate_python(template_args["endpoint"])
        expected_status_code = TypeAdapter(str).validate_python(str(template_args.get("expected_status_code", 200)))
        cronjob = make_base_cronjob(
            schedule=schedule,
            health_check_name=health_check_name,
        )
        cronjob.metadata.annotations["template_id"] = "simple_ping"
        cronjob.metadata.annotations["template_args"] = json.dumps(template_args)
        env = cronjob.spec.job_template.spec.template.spec.containers[0].env or []
        env.append(
            V1EnvVar(
                name="RESOURCE_HEALTH_RUNNER_SCRIPT",
                value="data:text/plain;base64,ZnJvbSBvcyBpbXBvcnQgZW52aXJvbgppbXBvcnQgcmVxdWVzdHMKCkdFTkVSSUNfRU5EUE9JTlQ6IHN0ciA9IGVudmlyb25bIkdFTkVSSUNfRU5EUE9JTlQiXQpFWFBFQ1RFRF9TVEFUVVNfQ09ERTogaW50ID0gaW50KGVudmlyb25bIkVYUEVDVEVEX1NUQVRVU19DT0RFIl0pCgoKZGVmIHRlc3RfcGluZygpIC0+IE5vbmU6CiAgICByZXNwb25zZSA9IHJlcXVlc3RzLmdldCgKICAgICAgICBHRU5FUklDX0VORFBPSU5ULAogICAgKQogICAgYXNzZXJ0IHJlc3BvbnNlLnN0YXR1c19jb2RlID09IEVYUEVDVEVEX1NUQVRVU19DT0RFCg==",
            )
        )
        env.append(
            V1EnvVar(
                name="GENERIC_ENDPOINT",
                value=endpoint,
            )
        )
        env.append(
            V1EnvVar(
                name="EXPECTED_STATUS_CODE",
                value=expected_status_code,
            )
        )
        cronjob.spec.job_template.spec.template.spec.containers[0].env = env
        return cronjob
