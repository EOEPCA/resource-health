from collections import defaultdict
from jsonschema import validate
import aiohttp
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
import logging
from os import environ
from pydantic import TypeAdapter
from typing import AsyncIterable, Optional, Self, override
import uuid
# import yaml

from api_interface import Json
from check_backends.check_backend import (
    AuthenticationObject,
    Check,
    CheckBackend,
    CheckId,
    CheckTemplate,
    CheckTemplateId,
    CronExpression,
)
from exceptions import (
    CheckException,
    CheckInternalError,
    CheckTemplateIdError,
    CheckIdError,
    CheckIdNonUniqueError,
    CheckConnectionError,
)

NAMESPACE: str = "resource-health"

logger = logging.getLogger("HEALTH_CHECK")


async def load_config() -> None:
    if "KUBERNETES_SERVICE_HOST" in environ:
        config.load_incluster_config()
    else:
        await config.load_kube_config()


def make_cronjob(
    name: str,
    schedule: Optional[str] = None,
    user_id: Optional[str] = None,
    health_check_name: Optional[str] = None,
    script: Optional[str] = None,
    requirements: Optional[str] = None,
) -> V1CronJob:
    OTEL_RESOURCE_ATTRIBUTES: Optional[str] = None
    if user_id and health_check_name:
        OTEL_RESOURCE_ATTRIBUTES = (
            f"k8s.cronjob.name={name},"
            f"user.id={user_id},"
            f"health_check.name={health_check_name}"
        )
    cronjob = V1CronJob(
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
    env = []
    if script:
        env.append(
            V1EnvVar(
                name="RESOURCE_HEALTH_RUNNER_SCRIPT",
                value=script,
            )
        )
    if OTEL_RESOURCE_ATTRIBUTES:
        env.append(
            V1EnvVar(
                name="OTEL_RESOURCE_ATTRIBUTES",
                value=OTEL_RESOURCE_ATTRIBUTES,
            )
        )
    if requirements:
        env.append(
            V1EnvVar(
                name="RESOURCE_HEALTH_RUNNER_REQUIREMENTS",
                value=requirements,
            )
        )
    if len(env) > 0:
        cronjob.spec.job_template.spec.template.spec.containers[0].env = env
    return cronjob


class K8sBackend(CheckBackend):
    def __init__(self: Self, service_name: str) -> None:
        self._service_name = service_name
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
            ),
        ]
        self._check_template_id_to_template = {
            template.id: template for template in check_templates
        }

    @override
    async def aclose(self: Self) -> None:
        pass

    def _get_check_template(self: Self, template_id: CheckTemplateId) -> CheckTemplate:
        if template_id not in self._check_template_id_to_template:
            raise CheckTemplateIdError(template_id)
        return self._check_template_id_to_template[template_id]

    def _make_check(self: Self, cronjob: V1CronJob) -> Check:
        env = cronjob.spec.job_template.spec.template.spec.containers[0].env
        script = [x.value for x in env if x.name == "RESOURCE_HEALTH_RUNNER_SCRIPT"]
        req = [x.value for x in env if x.name == "RESOURCE_HEALTH_RUNNER_REQUIREMENTS"]

        template_args = {}
        if len(script) > 0:
            template_args.update({"script": script[0]})
        if len(req) > 0:
            template_args.update({"requirements": req[0]})
        return Check(
            id=CheckId(cronjob.metadata.name),
            # metadata=cronjob.metadata.to_dict(),
            # TODO: TEMPLATE ID MUST NOT BE HARDCODED
            metadata={"template_id": "default_k8s_template", "template_args": template_args},
            schedule=CronExpression(cronjob.spec.schedule),
            outcome_filter={"resource_attributes": {"k8s.cronjob.name": cronjob.metadata.name}},
        )

    @override
    async def list_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        if ids is None:
            for template in self._check_template_id_to_template.values():
                yield template
        else:
            for id in ids:
                if id in self._check_template_id_to_template:
                    yield self._check_template_id_to_template[id]

    @override
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
        user_id = "Health BB user"
        health_check_name = TypeAdapter(str).validate_python(
            template_args["health_check.name"]
        )
        script = TypeAdapter(str).validate_python(template_args["script"])
        requirements = TypeAdapter(str | None).validate_python(
            template_args.get("requirements")
        )
        await load_config()
        async with ApiClient() as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                api_response = await api_instance.create_namespaced_cron_job(
                    namespace=NAMESPACE,
                    body=make_cronjob(
                        name=check_id,
                        schedule=schedule,
                        user_id=user_id,
                        health_check_name=health_check_name,
                        script=script,
                        requirements=requirements,
                    ),
                )
                logger.info(f"Succesfully created new cron job: {api_response}")
            except ApiException as e:
                logger.error(f"Failed to create new cron job: {e}")
                if e.status == 422:
                    raise CheckInternalError(f"Unprocessable content")
                raise e
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to create new cron job: {e}")
                raise CheckConnectionError("Cannot connect to cluster")
            check = Check(
                id=check_id,
                metadata={"template_id": template_id, "template_args": template_args},
                schedule=schedule,
                outcome_filter={"resource_attributes": {"k8s.cronjob.name": check_id}},
            )
        return check

    @override
    async def update_check(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
        template_id: CheckTemplateId | None = None,
        template_args: Json | None = None,
        schedule: CronExpression | None = None,
    ) -> Check:
        script = None
        requirements = None
        if template_args is not None:
            if template_id is not None:
                check_template = self._get_check_template(template_id)
                validate(template_args, check_template.arguments)
            script = TypeAdapter(str | None).validate_python(
                template_args.get("script")
            )
            requirements = TypeAdapter(str | None).validate_python(
                template_args.get("requirements")
            )
        await load_config()
        async with ApiClient() as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                api_response = await api_instance.patch_namespaced_cron_job(
                    name=check_id,
                    namespace=NAMESPACE,
                    body=make_cronjob(
                        name=check_id,
                        schedule=schedule,
                        script=script,
                        requirements=requirements,
                    ),
                )
                logger.info(f"Succesfully patched cron job: {api_response}")
            except ApiException as e:
                logger.error(f"Failed to patch cron job: {e}")
                if e.status == 422:
                    raise CheckInternalError(f"Unprocessable content")
                raise e
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to patch cron job: {e}")
                raise CheckConnectionError("Cannot connect to cluster")
            check = self._make_check(api_response)
        return check

    @override
    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        await load_config()
        async with ApiClient() as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                api_response = await api_instance.delete_namespaced_cron_job(
                    name=check_id,
                    namespace=NAMESPACE,
                )
                logger.info(f"Succesfully deleted cron job: {api_response}")
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to delete cron job: {e}")
                raise CheckConnectionError("Cannot connect to cluster")
            except ApiException as e:
                logger.info(f"Failed to delete check with id '{check_id}': {e}")
                if e.status == 404:
                    raise CheckIdError(f"Check with id '{check_id}' not found")
                else:
                    raise e
        return None

    @override
    async def list_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[Check]:
        await load_config()
        async with ApiClient() as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                cronjobs = await api_instance.list_namespaced_cron_job(NAMESPACE)
            except ApiException as e:
                logger.error(f"Failed to list cron jobs: {e}")
                raise e
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to list cron jobs: {e}")
                raise CheckConnectionError("Cannot connect to cluster")
            if ids is None:
                for cronjob in cronjobs.items:
                    yield self._make_check(cronjob)
            else:
                for cronjob in cronjobs.items:
                    if cronjob.metadata.name in ids:
                        yield self._make_check(cronjob)
