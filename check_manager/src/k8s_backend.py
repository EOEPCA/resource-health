from collections import defaultdict
from jsonschema import validate
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.client.models.v1_container import V1Container
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_cron_job_spec import V1CronJobSpec
from kubernetes_asyncio.client.models.v1_env_var import V1EnvVar
from kubernetes_asyncio.client.models.v1_job_spec import V1JobSpec
from kubernetes_asyncio.client.models.v1_pod_spec import V1PodSpec
from kubernetes_asyncio.client.models.v1_job_template_spec import V1JobTemplateSpec
from kubernetes_asyncio.client.models.v1_pod_template_spec import V1PodTemplateSpec
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from kubernetes_asyncio.client.rest import ApiException
from lib import (
    AuthenticationObject,
    Check,
    CheckBackend,
    CheckId,
    CheckTemplate,
    CheckTemplateId,
    CronExpression,
    Json,
)
import logging
from typing import AsyncIterable, Self
import uuid
# import yaml

NAMESPACE: str = "default"
# NAMESPACE: str = "RESOURCE_HEALTH_RUNNER"

logger = logging.getLogger("HEALTH_CHECK")


def make_cronjob(name: str, script: str, schedule: str) -> V1CronJob:
    return V1CronJob(
        api_version="batch/v1",
        kind="CronJob",
        metadata=V1ObjectMeta(name=name),
        spec=V1CronJobSpec(
            schedule=schedule,
            job_template=V1JobTemplateSpec(
                spec=V1JobSpec(
                    template=V1PodTemplateSpec(
                        spec=V1PodSpec(
                            containers=[
                                V1Container(
                                    name="healthcheck",
                                    image="victorlinrothsensmetry/healthcheck:v0.0.1",
                                    image_pull_policy="IfNotPresent",
                                    env=[
                                        V1EnvVar(
                                            name="RESOURCE_HEALTH_RUNNER_SCRIPT",
                                            value=script,
                                        ),
                                    ],
                                ),
                            ],
                            restart_policy="OnFailure",
                        ),
                    ),
                ),
            ),
        ),
    )


class K8sBackend(CheckBackend):
    def __init__(self: Self) -> None:
        self._check_template_id_to_template: dict[CheckTemplateId, CheckTemplate] = {}
        self._auth_to_id_to_check: defaultdict[
            AuthenticationObject, dict[CheckId, Check]
        ] = defaultdict(dict)
        check_templates = [
            CheckTemplate(
                id=CheckTemplateId("default_k8s_template"),
                metadata={
                    "label": "Default Kubernetes template",
                    "description": "Default template for checks in the Kubernetes backend.",
                },
                arguments={
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                        },
                        "requirements": {
                            "type": "string",
                        },
                    },
                    "required": ["script"],
                },
            ),
        ]
        self._check_template_id_to_template = {
            template.id: template for template in check_templates
        }

    async def aclose(self: Self) -> None:
        pass

    def _get_check_template(self: Self, template_id: CheckTemplateId) -> CheckTemplate:
        if template_id not in self._check_template_id_to_template:
            raise KeyError(f"Template id {template_id} not found")
        return self._check_template_id_to_template[template_id]

    def _make_check(self: Self, cronjob: V1CronJob) -> Check:
        return Check(
            id=CheckId(cronjob.metadata.name),
            metadata=cronjob.metadata.to_dict(),
            schedule=CronExpression(cronjob.spec.schedule),
            outcome_filter={},
        )

    async def list_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        if ids is None:
            for template in self._check_template_id_to_template.values():
                yield template
        else:
            for id in ids:
                yield self._get_check_template(id)

    async def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> Check:
        check_template = self._get_check_template(template_id)
        validate(template_args, check_template.arguments)
        check_id = CheckId(str(uuid.uuid4()))
        await config.load_kube_config()
        async with ApiClient() as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                api_response = await api_instance.create_namespaced_cron_job(
                    namespace=NAMESPACE,
                    body=make_cronjob(
                        check_id,
                        template_args["script"],
                        schedule,
                    ),
                )
                logger.info(f"Succesfully created new cron job: {api_response}")
            except ApiException as e:
                logger.error(f"Failed to create new cron job: {e}")
            check = Check(
                id=check_id,
                metadata={"template_id": template_id, "template_args": template_args},
                schedule=schedule,
                outcome_filter={"test.id": check_id},
            )
        return check

    async def update_check(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
        template_id: CheckTemplateId | None = None,
        template_args: Json | None = None,
        schedule: CronExpression | None = None,
    ) -> Check:
        return Check()

    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        await config.load_kube_config()
        async with ApiClient() as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                api_response = await api_instance.delete_namespaced_cron_job(
                    name=check_id,
                    namespace=NAMESPACE,
                )
                logger.info(f"Succesfully deleted cron job: {api_response}")
            except ApiException as e:
                logger.error(f"Failed to delete check with id '{check_id}': {e}")
        return None

    async def list_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[Check]:
        await config.load_kube_config()
        async with ApiClient() as api_client:
            api_instance = client.BatchV1Api(api_client)
            cronjobs = await api_instance.list_namespaced_cron_job(NAMESPACE)
            if ids is None:
                for cronjob in cronjobs.items:
                    yield self._make_check(cronjob)
            else:
                for cronjob in cronjobs.items:
                    if cronjob.metadata.name in ids:
                        yield self._make_check(cronjob)


async def list_checks(check_backend: CheckBackend) -> None:
    print("List of checks")
    async for check in check_backend.list_checks(AuthenticationObject("dummy")):
        print(f"-Check id: {check.id}")
        print(f" Schedule: {check.schedule}")


# For testing the backend functions
if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO)
    logging.basicConfig(level=logging.WARNING)

    check_backend: CheckBackend = K8sBackend()

    auth_obj = AuthenticationObject("dummy")

    import asyncio

    check: Check = asyncio.run(
        check_backend.new_check(
            auth_obj=auth_obj,
            template_id=CheckTemplateId("Null"),
            template_args=dict(),
            schedule=CronExpression("1 * * * *"),
        )
    )

    asyncio.run(list_checks(check_backend))

    asyncio.run(
        check_backend.remove_check(
            auth_obj=auth_obj,
            check_id=check.id,
        )
    )
