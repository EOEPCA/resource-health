import logging
import re
from typing import AsyncIterable, Callable, Self, override
import uuid

from jsonschema import validate
import aiohttp
from kubernetes_asyncio import client  # , config
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.client.rest import ApiException
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_job import V1Job
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from kubernetes_asyncio.client.models.v1_owner_reference import V1OwnerReference

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
from exceptions import (
    CheckConnectionError,
    CronExpressionValidationError,
)

NAMESPACE: str = "resource-health"

logger = logging.getLogger("HEALTH_CHECK")

minute_pattern = r"(\*|[0-5]?\d)(/\d+)?([-,][0-5]?\d)*"
hour_pattern = r"(\*|[01]?\d|2[0-3])(/\d+)?([-,]([01]?\d|2[0-3]))*"
day_of_month_pattern = r"(\*|[1-9]|[12]\d|3[01])(/\d+)?([-,]([1-9]|[12]\d|3[01]))*"
month_pattern = r"(\*|1[0-2]|0?[1-9])(/\d+)?([-,](1[0-2]|0?[1-9]))*"
day_of_week_pattern = r"(\*|[0-7])(/\d+)?([-,][0-7])*"

cron_pattern = " ".join([
    minute_pattern,
    hour_pattern,
    day_of_month_pattern,
    month_pattern,
    day_of_week_pattern,
])


def validate_kubernetes_cron(cron_expr: str) -> None:
    if not re.match(cron_pattern, cron_expr):
        raise CronExpressionValidationError.create(
            "Invalid cron expression for use with Kubernetes"
        )


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


class K8sBackend(CheckBackend[AuthenticationObject]):
    def __init__(
        self: Self,
        template_dirs: list[str],
        authentication: dict[str, Callable],
    ) -> None:
        self._templates: dict[str, CronjobMaker] = load_templates(
            template_dirs
        )
        self._authentication = authentication

    @override
    async def aclose(self: Self) -> None:
        pass

    @override
    async def get_check_templates(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        auth = self._authentication["on_auth"](auth_obj)
        if auth is None:
            raise Exception("Invalid credentials")
        template_ids = list(self._templates.keys())
        template_access = self._authentication["template_access"]

        for id in template_ids:
            if (
                template_access(auth, id) and
                (ids is None or id in ids)
            ):
                cronjob_template = self._templates.get(id)
                if cronjob_template is not None:
                    yield cronjob_template.get_check_template()

    @override
    async def create_check(
        self: Self,
        auth_obj: AuthenticationObject,
        attributes: InCheckAttributes,
    ) -> OutCheck:
        auth = self._authentication["on_auth"](auth_obj)
        if auth is None:
            raise Exception("Invalid credentials")
        configuration = await self._authentication["create_check_configuration"](auth)
        namespace = self._authentication["get_namespace"](auth)
        userinfo = await self._authentication["get_userinfo"](auth, configuration)
        template_access = self._authentication["template_access"]
        tag_cronjob = self._authentication["tag_cronjob"]

        template_id = attributes.metadata.template_id
        template_denied = not template_access(
            auth, template_id
        )
        template = self._templates.get(template_id)

        if template_denied or template is None:
            raise CheckTemplateIdError.create(template_id)

        check_template = template.get_check_template()
        validate(
            attributes.metadata.template_args,
            check_template.attributes.arguments,
        )
        validate_kubernetes_cron(attributes.schedule)
        cronjob = tag_cronjob(
            auth,
            template.make_cronjob(
                metadata=attributes.metadata,
                schedule=attributes.schedule,
                userinfo=userinfo,
            ),
        )

        async with ApiClient(configuration) as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                api_response = await api_instance.create_namespaced_cron_job(
                    namespace=namespace,
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
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
    ) -> None:
        auth = self._authentication["on_auth"](auth_obj)
        if auth is None:
            raise Exception("Invalid!")
        configuration = await self._authentication["remove_check_configuration"](auth)
        namespace = self._authentication["get_namespace"](auth)
        cronjob_access = self._authentication["cronjob_access"]

        async with ApiClient(configuration) as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                cronjob = await api_instance.read_namespaced_cron_job(
                    name=check_id,
                    namespace=namespace,
                )
                if not cronjob_access(auth, cronjob):
                    raise CheckIdError.create(check_id)

                api_response = await api_instance.delete_namespaced_cron_job(
                    name=check_id,
                    namespace=namespace,
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
        auth = self._authentication["on_auth"](auth_obj)
        if auth is None:
            raise Exception("Invalid!")
        configuration = await self._authentication["get_checks_configuration"](auth)
        namespace = self._authentication["get_namespace"](auth)
        cronjob_access = self._authentication["cronjob_access"]

        async with ApiClient(configuration) as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                cronjobs = await api_instance.list_namespaced_cron_job(
                    namespace=namespace,
                )
            except ApiException as e:
                logger.error(f"Failed to list cron jobs: {e}")
                raise e
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to list cron jobs: {e}")
                raise CheckConnectionError.create("Cannot connect to cluster")
            template_id: str | None

            for cronjob in cronjobs.items:
                if (
                    cronjob_access(auth, cronjob) and
                    (ids is None or cronjob.metadata.name in ids)
                ):
                    template_id = None
                    if cronjob.metadata and cronjob.metadata.annotations:
                        template_id = cronjob.metadata.annotations.get("template_id")
                    template = self._templates.get(template_id or "")
                    if template is not None:
                        yield template.make_check(cronjob)
                    else:
                        yield default_make_check(cronjob)

    @override
    async def run_check(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
    ) -> None:
        auth = self._authentication["on_auth"](auth_obj)
        if auth is None:
            raise Exception("Invalid!")
        configuration = await self._authentication["run_check_configuration"](auth)
        namespace = self._authentication["get_namespace"](auth)
        cronjob_access = self._authentication["cronjob_access"]

        async with ApiClient(configuration) as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                cronjob = await api_instance.read_namespaced_cron_job(
                    name=check_id,
                    namespace=namespace,
                )
                if not cronjob_access(auth, cronjob):
                    raise CheckIdError.create(check_id)

                api_response = await api_instance.create_namespaced_job(
                    namespace=namespace,
                    body=job_from(cronjob),
                )
                logger.info(f"Succesfully created new job: {api_response}")
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
