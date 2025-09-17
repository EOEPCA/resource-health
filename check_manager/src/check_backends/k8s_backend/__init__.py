import logging
import re
from typing import AsyncIterable, Callable, Self, override
import uuid
import os

from jsonschema import validate
import aiohttp
from kubernetes_asyncio import client  # , config
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.client.rest import ApiException
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_job import V1Job
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from kubernetes_asyncio.client.models.v1_owner_reference import V1OwnerReference

from plugin_utils.runner import call_hooks_until_not_none, call_hooks_ignore_results
from eoepca_api_utils.exceptions import APIInternalError
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
from check_hooks import call_hooks_check_if_allow
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

cron_pattern = " ".join(
    [
        minute_pattern,
        hour_pattern,
        day_of_month_pattern,
        month_pattern,
        day_of_week_pattern,
    ]
)


def validate_kubernetes_cron(cron_expr: str) -> None:
    if not re.match(cron_pattern, cron_expr):
        raise CronExpressionValidationError(
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
        ),
    )


GET_K8S_CONFIG_HOOK_NAME = (
    os.environ.get("RH_CHECK_GET_K8S_CONFIG_HOOK_NAME") or "get_k8s_config"
)
GET_K8S_NAMESPACE_HOOK_NAME = (
    os.environ.get("RH_CHECK_GET_K8S_NAMESPACE_HOOK_NAME") or "get_k8s_namespace"
)
ON_K8S_CRONJOB_ACCESS_HOOK_NAME = (
    os.environ.get("RH_CHECK_ON_K8S_CRONJOB_ACCESS_HOOK_NAME")
    or "on_k8s_cronjob_access"
)
ON_K8S_CRONJOB_CREATE_HOOK_NAME = (
    os.environ.get("RH_CHECK_ON_K8S_CRONJOB_CREATE_HOOK_NAME")
    or "on_k8s_cronjob_create"
)
ON_K8S_CRONJOB_REMOVE_HOOK_NAME = (
    os.environ.get("RH_CHECK_ON_K8S_CRONJOB_REMOVE_HOOK_NAME")
    or "on_k8s_cronjob_remove"
)
ON_K8S_CRONJOB_RUN_HOOK_NAME = (
    os.environ.get("RH_CHECK_ON_K8S_CRONJOB_RUN_HOOK_NAME") or "on_k8s_cronjob_run"
)


class K8sBackend(CheckBackend[AuthenticationObject]):
    def __init__(
        self: Self,
        template_dirs: list[str],
        hooks: dict[str, list[Callable]],
    ) -> None:
        self._templates: dict[str, CronjobMaker] = load_templates(template_dirs)
        self._hooks = hooks

    @override
    async def aclose(self: Self) -> None:
        pass

    @override
    async def get_check_templates(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        if ids is None:
            ids = [CheckTemplateId(x) for x in self._templates.keys()]

        for template_id in ids:
            cronjob_template = self._templates.get(template_id)

            if cronjob_template is None:
                raise KeyError(f"missing template id {template_id}")

            yield cronjob_template.get_check_template()

    @override
    async def create_check(
        self: Self,
        auth_obj: AuthenticationObject,
        attributes: InCheckAttributes,
    ) -> OutCheck:
        if GET_K8S_CONFIG_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_K8S_CONFIG_HOOK_NAME} ($RH_CHECK_GET_K8S_CONFIG) when using the k8s backend"
            )

        if GET_K8S_NAMESPACE_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_K8S_NAMESPACE_HOOK_NAME} ($RH_CHECK_GET_K8S_NAMESPACE_HOOK_NAME) when using the k8s backend"
            )

        configuration = await call_hooks_until_not_none(
            self._hooks[GET_K8S_CONFIG_HOOK_NAME], auth_obj
        )
        namespace = await call_hooks_until_not_none(
            self._hooks[GET_K8S_NAMESPACE_HOOK_NAME], auth_obj
        )

        template_id = attributes.metadata.template_id
        template = self._templates.get(template_id)

        if template is None:
            raise CheckTemplateIdError(template_id)

        check_template = template.get_check_template()
        validate(
            attributes.metadata.template_args,
            check_template.attributes.arguments,
        )
        validate_kubernetes_cron(attributes.schedule)

        async with ApiClient(configuration) as api_client:
            cronjob = template.make_cronjob(
                metadata=attributes.metadata,
                schedule=attributes.schedule,
                userinfo=auth_obj,
            )

            if ON_K8S_CRONJOB_CREATE_HOOK_NAME in self._hooks:
                await call_hooks_ignore_results(
                    self._hooks[ON_K8S_CRONJOB_CREATE_HOOK_NAME],
                    auth_obj,
                    api_client,
                    cronjob,
                )

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
                    raise APIInternalError("Unprocessable content")
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
        if GET_K8S_CONFIG_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_K8S_CONFIG_HOOK_NAME} ($RH_CHECK_GET_K8S_CONFIG) when using the k8s backend"
            )

        if GET_K8S_NAMESPACE_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_K8S_NAMESPACE_HOOK_NAME} ($RH_CHECK_GET_K8S_NAMESPACE_HOOK_NAME) when using the k8s backend"
            )

        configuration = await call_hooks_until_not_none(
            self._hooks[GET_K8S_CONFIG_HOOK_NAME], auth_obj
        )
        namespace = await call_hooks_until_not_none(
            self._hooks[GET_K8S_NAMESPACE_HOOK_NAME], auth_obj
        )

        async with ApiClient(configuration) as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                cronjob = await api_instance.read_namespaced_cron_job(
                    name=check_id,
                    namespace=namespace,
                )

                if ON_K8S_CRONJOB_ACCESS_HOOK_NAME in self._hooks:
                    await call_hooks_ignore_results(
                        self._hooks[ON_K8S_CRONJOB_ACCESS_HOOK_NAME],
                        auth_obj,
                        check_id,
                        api_client,
                        cronjob,
                    )

                if ON_K8S_CRONJOB_REMOVE_HOOK_NAME in self._hooks:
                    await call_hooks_ignore_results(
                        self._hooks[ON_K8S_CRONJOB_REMOVE_HOOK_NAME],
                        auth_obj,
                        api_client,
                        cronjob,
                    )

                api_response = await api_instance.delete_namespaced_cron_job(
                    name=check_id,
                    namespace=namespace,
                )
                logger.info(f"Succesfully deleted cron job: {api_response}")
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to delete cron job: {e}")
                raise CheckConnectionError("Cannot connect to cluster")
            except ApiException as e:
                logger.info(f"Failed to delete check with id '{check_id}': {e}")
                if e.status == 404:
                    raise CheckIdError(check_id)
                else:
                    raise e
        return None

    @override
    async def get_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[OutCheck]:
        if GET_K8S_CONFIG_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_K8S_CONFIG_HOOK_NAME} ($RH_CHECK_GET_K8S_CONFIG) when using the k8s backend"
            )

        if GET_K8S_NAMESPACE_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_K8S_NAMESPACE_HOOK_NAME} ($RH_CHECK_GET_K8S_NAMESPACE_HOOK_NAME) when using the k8s backend"
            )

        configuration = await call_hooks_until_not_none(
            self._hooks[GET_K8S_CONFIG_HOOK_NAME], auth_obj
        )
        namespace = await call_hooks_until_not_none(
            self._hooks[GET_K8S_NAMESPACE_HOOK_NAME], auth_obj
        )

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
                raise CheckConnectionError("Cannot connect to cluster")
            template_id: str | None

            for cronjob in cronjobs.items:
                check_id = cronjob.metadata.name
                if (ids is None or cronjob.metadata.name in ids) and (
                    ON_K8S_CRONJOB_ACCESS_HOOK_NAME not in self._hooks
                    or await call_hooks_check_if_allow(
                        self._hooks[ON_K8S_CRONJOB_ACCESS_HOOK_NAME],
                        auth_obj,
                        check_id,
                        api_client,
                        cronjob,
                    )
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
        if GET_K8S_CONFIG_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_K8S_CONFIG_HOOK_NAME} ($RH_CHECK_GET_K8S_CONFIG) when using the k8s backend"
            )

        if GET_K8S_NAMESPACE_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_K8S_NAMESPACE_HOOK_NAME} ($RH_CHECK_GET_K8S_NAMESPACE_HOOK_NAME) when using the k8s backend"
            )

        configuration = await call_hooks_until_not_none(
            self._hooks[GET_K8S_CONFIG_HOOK_NAME], auth_obj
        )
        namespace = await call_hooks_until_not_none(
            self._hooks[GET_K8S_NAMESPACE_HOOK_NAME], auth_obj
        )

        async with ApiClient(configuration) as api_client:
            api_instance = client.BatchV1Api(api_client)
            try:
                cronjob = await api_instance.read_namespaced_cron_job(
                    name=check_id,
                    namespace=namespace,
                )

                if ON_K8S_CRONJOB_ACCESS_HOOK_NAME in self._hooks:
                    await call_hooks_ignore_results(
                        self._hooks[ON_K8S_CRONJOB_ACCESS_HOOK_NAME],
                        auth_obj,
                        check_id,
                        api_client,
                        cronjob,
                    )

                if ON_K8S_CRONJOB_RUN_HOOK_NAME in self._hooks:
                    await call_hooks_ignore_results(
                        self._hooks[ON_K8S_CRONJOB_RUN_HOOK_NAME],
                        auth_obj,
                        api_client,
                        cronjob,
                    )

                api_response = await api_instance.create_namespaced_job(
                    namespace=namespace,
                    body=job_from(cronjob),
                )
                logger.info(f"Succesfully created new job: {api_response}")
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Failed to delete cron job: {e}")
                raise CheckConnectionError("Cannot connect to cluster")
            except ApiException as e:
                logger.info(f"Failed to delete check with id '{check_id}': {e}")
                if e.status == 404:
                    raise CheckIdError(check_id)
                else:
                    raise e
        return None
