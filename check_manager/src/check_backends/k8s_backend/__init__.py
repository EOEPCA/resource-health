from jsonschema import validate
import aiohttp
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.client.rest import ApiException
import logging
from os import environ
from typing import AsyncIterable, Self, override

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
from check_backends.k8s_backend.templates import TemplateFactory
from exceptions import (
    CheckInternalError,
    CheckTemplateIdError,
    CheckIdError,
    CheckConnectionError,
)

NAMESPACE: str = "resource-health"

logger = logging.getLogger("HEALTH_CHECK")


async def load_config() -> None:
    if "KUBERNETES_SERVICE_HOST" in environ:
        config.load_incluster_config()
    else:
        await config.load_kube_config()


class K8sBackend(CheckBackend):
    def __init__(
        self: Self,
        template_dirs: list[str],
        api_client: ApiClient = None
    ) -> None:
        self._template_dirs: list[str] = template_dirs
        self._api_client = api_client or ApiClient()

    def _load_templates(self: Self) -> None:
        for dir in self._template_dirs:
            TemplateFactory.load_templates_from_directory(dir)

    @override
    async def aclose(self: Self) -> None:
        pass

    @override
    async def list_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        self._load_templates()
        template_ids = TemplateFactory.list_templates()
        if ids is None:
            for id in template_ids:
                yield TemplateFactory.get_template(id).get_check_template()
        else:
            for id in ids:
                if id in template_ids:
                    yield TemplateFactory.get_template(id).get_check_template()

    @override
    async def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> Check:
        self._load_templates()
        template = TemplateFactory.get_template(template_id)
        if template is None:
            raise CheckTemplateIdError(f"No template found for ID: {template_id}")
        check_template = template.get_check_template()
        validate(template_args, check_template.arguments)
        cronjob = template.make_cronjob(
            template_args=template_args,
            schedule=schedule
        )
        await load_config()
        async with self._api_client as api_client:
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
                    raise CheckInternalError(f"Unprocessable content")
                raise e
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to create new cron job: {e}")
                raise CheckConnectionError("Cannot connect to cluster")
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
    #     async with self._api_client as api_client:
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
        async with self._api_client as api_client:
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
        async with self._api_client as api_client:
            self._load_templates()
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
                    template_id = cronjob.metadata.annotations["template_id"]
                    template = TemplateFactory.get_template(template_id)
                    yield template.make_check(cronjob)
            else:
                for cronjob in cronjobs.items:
                    if cronjob.metadata.name in ids:
                        template_id = cronjob.metadata.annotations["template_id"]
                        template = TemplateFactory.get_template(template_id)
                        yield template.make_check(cronjob)
