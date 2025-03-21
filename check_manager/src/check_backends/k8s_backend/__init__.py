from jsonschema import validate
import aiohttp
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.client.rest import ApiException
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_job import V1Job
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from kubernetes_asyncio.client.models.v1_owner_reference import V1OwnerReference
import logging
from os import environ
from typing import AsyncIterable, Self, override
import uuid

from api_utils.exceptions import APIInternalError
from check_backends.check_backend import (
    AuthenticationObject,
    CheckBackend,
    CheckId,
    CheckIdError,
    CheckTemplate,
    CheckTemplateId,
    CheckTemplateIdError,
    InCheckAttributes,
    OutCheck,
)
from check_backends.k8s_backend.templates import (
    CronjobMaker,
    load_templates,
    default_make_check,
)
from exceptions import CheckConnectionError

NAMESPACE: str = "resource-health"

logger = logging.getLogger("HEALTH_CHECK")


async def load_config() -> None:
    if "KUBERNETES_SERVICE_HOST" in environ:
        config.load_incluster_config()
    else:
        await config.load_kube_config()


def job_from(cronjob: V1CronJob):
    return V1Job(
        spec=cronjob.spec.job_template.spec,
        metadata=V1ObjectMeta(
            name=str(uuid.uuid4()),
            owner_references=[
                V1OwnerReference(
                    api_version="batch/v1",
                    controller=True,
                    kind="Cronjob",
                    name=cronjob.metadata.name,
                    uid=cronjob.metadata.uid,
                ),
            ],
        )
    )


class K8sBackend(CheckBackend):
    def __init__(
        self: Self, template_dirs: list[str], api_client: type[ApiClient] | None = None
    ) -> None:
        self._templates: dict[str, CronjobMaker] = load_templates(template_dirs)
        self._api_client: type[ApiClient] = api_client or ApiClient

    @override
    async def aclose(self: Self) -> None:
        pass

    @override
    async def get_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        # TODO: See if there is a way to loop directly over the check templates
        template_ids = list(self._templates.keys())
        # print(f"template_ids {template_ids}")
        if ids is None:
            for id in template_ids:
                cronjob_template = self._templates.get(id)
                if cronjob_template is not None:
                    yield cronjob_template.get_check_template()
        else:
            for id in ids:
                if id in template_ids:
                    cronjob_template = self._templates.get(id)
                    if cronjob_template is not None:
                        yield cronjob_template.get_check_template()

    @override
    async def create_check(
        self: Self, auth_obj: AuthenticationObject, attributes: InCheckAttributes
    ) -> OutCheck:
        template = self._templates.get(attributes.metadata.template_id)
        if template is None:
            raise CheckTemplateIdError.create(attributes.metadata.template_id)
        check_template = template.get_check_template()
        validate(attributes.metadata.template_args, check_template.attributes.arguments)
        cronjob = template.make_cronjob(
            metadata=attributes.metadata,
            schedule=attributes.schedule,
        )
        await load_config()
        async with self._api_client() as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                api_response = await api_instance.create_namespaced_cron_job(
                    namespace=NAMESPACE,
                    body=cronjob,
                )
                logger.info(f"Succesfully created new cron job: {api_response}")
            except ApiException as e:
                logger.error(f"Failed to create new cron job: {e}")
                if e.status == 422:
                    raise APIInternalError.create("Unprocessable content")
                raise e
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to create new cron job: {e}")
                raise CheckConnectionError.create("Cannot connect to cluster")
            check = template.make_check(api_response)
        return check

    # @override
    # async def update_check(
    #     self: Self,
    #     auth_obj: AuthenticationObject,
    #     check_id: CheckId,
    #     template_id: CheckTemplateId | None = None,
    #     template_args: Json | None = None,
    #     schedule: CronExpression | None = None,
    # ) -> Check:
    #     script = None
    #     requirements = None
    #     if template_args is not None:
    #         if template_id is not None:
    #             check_template = self._get_check_template(template_id)
    #             validate(template_args, check_template.arguments)
    #         script = TypeAdapter(str | None).validate_python(
    #             template_args.get("script")
    #         )
    #         requirements = TypeAdapter(str | None).validate_python(
    #             template_args.get("requirements")
    #         )
    #     await load_config()
    #     async with self._api_client() as api_client:
    #         api_instance = client.BatchV1Api(api_client)
    #         try:
    #             api_response = await api_instance.patch_namespaced_cron_job(
    #                 name=check_id,
    #                 namespace=NAMESPACE,
    #                 body=make_cronjob(
    #                     name=check_id,
    #                     schedule=schedule,
    #                     script=script,
    #                     requirements=requirements,
    #                 ),
    #             )
    #             logger.info(f"Succesfully patched cron job: {api_response}")
    #         except ApiException as e:
    #             logger.error(f"Failed to patch cron job: {e}")
    #             if e.status == 422:
    #                 raise CheckInternalError(f"Unprocessable content")
    #             raise e
    #         except aiohttp.ClientConnectionError as e:
    #             logger.error(f"Failed to patch cron job: {e}")
    #             raise CheckConnectionError("Cannot connect to cluster")
    #         check = self._make_check(api_response)
    #     return check

    @override
    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        await load_config()
        async with self._api_client() as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                api_response = await api_instance.delete_namespaced_cron_job(
                    name=check_id,
                    namespace=NAMESPACE,
                )
                logger.info(f"Succesfully deleted cron job: {api_response}")
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to delete cron job: {e}")
                raise CheckConnectionError.create("Cannot connect to cluster")
            except ApiException as e:
                logger.info(f"Failed to delete check with id '{check_id}': {e}")
                if e.status == 404:
                    raise CheckIdError.create(check_id)
                else:
                    raise e
        return None

    @override
    async def get_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[OutCheck]:
        await load_config()
        async with self._api_client() as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                cronjobs = await api_instance.list_namespaced_cron_job(
                    namespace=NAMESPACE
                )
            except ApiException as e:
                logger.error(f"Failed to list cron jobs: {e}")
                raise e
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to list cron jobs: {e}")
                raise CheckConnectionError.create("Cannot connect to cluster")
            template_id: str | None
            if ids is None:
                for cronjob in cronjobs.items:
                    template_id = None
                    if cronjob.metadata and cronjob.metadata.annotations:
                        template_id = cronjob.metadata.annotations.get("template_id")
                    template = self._templates.get(template_id or "")
                    if template is not None:
                        yield template.make_check(cronjob)
                    else:
                        yield default_make_check(cronjob)
            else:
                for cronjob in cronjobs.items:
                    if cronjob.metadata.name in ids:
                        template_id = None
                        if cronjob.metadata and cronjob.metadata.annotations:
                            template_id = cronjob.metadata.annotations.get(
                                "template_id"
                            )
                        template = self._templates.get(template_id or "")
                        if template is not None:
                            yield template.make_check(cronjob)
                        else:
                            yield default_make_check(cronjob)

    @override
    async def run_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        await load_config()
        async with self._api_client() as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                cronjob = await api_instance.read_namespaced_cron_job(
                    name=check_id,
                    namespace=NAMESPACE,
                )
                api_response = await api_instance.create_namespaced_job(
                    namespace=NAMESPACE,
                    body=job_from(cronjob),
                )
                logger.info(f"Succesfully created new cron job: {api_response}")
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to delete cron job: {e}")
                raise CheckConnectionError.create("Cannot connect to cluster")
            except ApiException as e:
                logger.info(f"Failed to delete check with id '{check_id}': {e}")
                if e.status == 404:
                    raise CheckIdError.create(check_id)
                else:
                    raise e
        return None
