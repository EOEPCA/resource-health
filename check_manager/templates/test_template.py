from typing import override

from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob

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


class TestTemplate(CronjobTemplate):
    @override
    def get_check_template(self) -> CheckTemplate:
        return CheckTemplate(
            id=CheckTemplateId("test_template"),
            attributes=CheckTemplateAttributes(
                metadata=CheckTemplateMetadata(
                    label="Test template",
                    description="Template for testing. Checks do nothing but write to logs.",
                ),
                arguments={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        )

    @override
    def make_cronjob(
        self,
        template_args: Json,
        schedule: CronExpression,
    ) -> V1CronJob:
        cronjob = make_base_cronjob(
            schedule=schedule,
            container_image="busybox:1.28",
        )
        cronjob.spec.job_template.spec.template.spec.containers[0].command = [
            "/bin/sh",
            "-c",
            "date; echo Running test check",
        ]
        return cronjob
