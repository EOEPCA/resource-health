import json
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


class SimplePing(CronjobTemplate):
    @override
    def get_check_template(self) -> CheckTemplate:
        return CheckTemplate(
            id=CheckTemplateId("simple_ping"),
            attributes=CheckTemplateAttributes(
                metadata=CheckTemplateMetadata(
                    label="Simple ping template",
                    description="Simple template with preset script for pinging single endpoint.",
                ),
                arguments={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "object",
                    "properties": {
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
                        "endpoint",
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
        endpoint = TypeAdapter(str).validate_python(template_args["endpoint"])
        expected_status_code = TypeAdapter(str).validate_python(
            str(template_args.get("expected_status_code", 200))
        )
        cronjob = make_base_cronjob(
            schedule=schedule,
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
