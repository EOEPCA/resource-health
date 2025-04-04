from typing import Optional, override, Generic, TypeVar, Any, Callable
import json
from abc import abstractmethod
import os
import base64

from kubernetes_asyncio.client.models.v1_container import V1Container
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_cron_job_spec import V1CronJobSpec
from kubernetes_asyncio.client.models.v1_job_spec import V1JobSpec
from kubernetes_asyncio.client.models.v1_pod_spec import V1PodSpec
from kubernetes_asyncio.client.models.v1_job_template_spec import V1JobTemplateSpec
from kubernetes_asyncio.client.models.v1_pod_template_spec import V1PodTemplateSpec
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta

import pydantic
from ..templates import CronExpression, CronjobTemplate
from api_utils.json_api_types import Json
from check_backends.check_backend import (
    CheckId,
    CheckTemplate,
    CheckTemplateId,
    CheckTemplateAttributes,
    CheckTemplateMetadata,
    CronExpression,
    InCheckMetadata,
    OutCheck,
    OutCheckAttributes,
    OutCheckMetadata,
    OutcomeFilter,
)
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_env_var import V1EnvVar
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from kubernetes_asyncio.client.models.v1_volume_mount import V1VolumeMount
from kubernetes_asyncio.client.models.v1_volume import V1Volume
from kubernetes_asyncio.client.models.v1_secret_volume_source import (
    V1SecretVolumeSource,
)
from kubernetes_asyncio.client.models.v1_env_var_source import V1EnvVarSource
from kubernetes_asyncio.client.models.v1_secret_key_selector import V1SecretKeySelector

DEFAULT_RUNNER_IMAGE: str = (
    os.environ.get("RH_CHECK_K8S_DEFAULT_RUNNER_IMAGE")
    or "docker.io/eoepca/healthcheck_runner:2.0.0-beta2"
)

DEFAULT_OIDC_MITMPROXY_IMAGE: str = (
    os.environ.get("RH_CHECK_K8S_DEFAULT_OIDC_MITMPROXY_IMAGE")
    or "docker.io/eoepca/mitmproxy_oidc:v0.3.0-internal2"
)

def make_base_cronjob(
    schedule: CronExpression,
    container_image: Optional[str] = DEFAULT_RUNNER_IMAGE,
) -> V1CronJob:
    return V1CronJob(
        api_version="batch/v1",
        kind="CronJob",
        metadata=V1ObjectMeta(
            annotations={},
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
                                    image=container_image,
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


def container(
    name: str,
    image: str,
    *,
    env: dict[str, str] | None = None,
    secret_env: dict[str, tuple[str, str]] | None = None,
    args: list[str] | None = None,
    command: list[str] | None = None,
    image_pull_policy: str | None = "IfNotPresent",
) -> V1Container:
    return V1Container(
        name=name,
        image=image,
        args=args,
        command=command,
        env=[V1EnvVar(name=name, value=value) for name, value in (env or {}).items()]
        + [
            V1EnvVar(
                name=name,
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(name=secret_name, key=secret_key)
                ),
            )
            for name, (secret_name, secret_key) in (secret_env or {}).items()
        ],
        image_pull_policy=image_pull_policy,
    )


def runner_container(
    script_url: str,
    requirements_url: str | None = None,
    *,
    image: str = DEFAULT_RUNNER_IMAGE,
    name: str = "healthcheck",
    env: dict[str, str] | None = None,
    secret_env: dict[str, tuple[str, str]] | None = None,
    args: list[str] | None = None,
    command: list[str] | None = None,
    image_pull_policy: str | None = "IfNotPresent",
) -> V1Container:
    if env is None:
        env = {}
    else:
        env = env.copy()

    env["RESOURCE_HEALTH_RUNNER_SCRIPT"] = script_url
    if requirements_url is not None:
        env["RESOURCE_HEALTH_RUNNER_REQUIREMENTS"] = requirements_url

    return container(
        image=image,
        name=name,
        env=env,
        secret_env=secret_env,
        args=args,
        command=command,
        image_pull_policy=image_pull_policy,
    )


def oidc_mitmproxy_container(
    remote_domain: str,
    *,
    openid_connect_url: str,
    openid_client_id: tuple[str, str],
    openid_client_secret: tuple[str, str],
    openid_audience: str = "account",
    refresh_token_secret: tuple[str, str],
    tls_verify: bool = False,
    image: str = DEFAULT_OIDC_MITMPROXY_IMAGE,
    name: str = "proxy-oidc-sidecar",
    env: dict[str, str] | None = None,
    secret_env: dict[str, tuple[str, str]] | None = None,
    args: list[str] | None = None,
    command: list[str] | None = None,
    image_pull_policy: str | None = "IfNotPresent",
) -> V1Container:
    if env is None:
        env = {}
    else:
        env = env.copy()

    if secret_env is None:
        secret_env = {}
    else:
        secret_env = secret_env.copy()

    env["OPEN_ID_CONNECT_URL"] = openid_connect_url
    env["OPEN_ID_CONNECT_AUDIENCE"] = openid_audience
    env["REMOTE_PROTECTED_DOMAIN"] = remote_domain

    if not tls_verify:
        env["TLS_NO_VERIFY"] = "true"

    secret_env["OPEN_ID_REFRESH_TOKEN"] = refresh_token_secret
    secret_env["OPEN_ID_CONNECT_CLIENT_ID"] = openid_client_id
    secret_env["OPEN_ID_CONNECT_CLIENT_SECRET"] = openid_client_secret

    return container(
        image=image,
        name=name,
        env=env,
        secret_env=secret_env,
        args=args,
        command=command,
        image_pull_policy=image_pull_policy,
    )


ArgumentType = TypeVar("ArgumentType", bound=pydantic.BaseModel)


def cronjob_template[ArgumentType](
    template_id: str,
    argument_type: type[ArgumentType],
    *,
    label: str | None = None,
    description: str | None = None,
    template_metadata: dict[str, str] | None = None,
    annotations: Callable[[ArgumentType], dict[str, str]]
    | dict[str, str]
    | None = None,
    containers: Callable[[ArgumentType], list[V1Container]],
) -> type[CronjobTemplate]:
    class SimpleCronjobTemplate(CronjobTemplate):
        @override
        def get_check_template(self) -> CheckTemplate:
            if template_metadata is not None:
                metadata: dict[str, str] = template_metadata.copy()
            else:
                metadata = {}

            if label is not None:
                metadata["label"] = label
            if description is not None:
                metadata["description"] = description

            schema_obj: dict[str, Any] = argument_type.model_json_schema()  # type: ignore
            schema_obj["$schema"] = "http://json-schema.org/draft-07/schema"

            return CheckTemplate(
                id=CheckTemplateId(template_id),
                attributes=CheckTemplateAttributes(
                    metadata=CheckTemplateMetadata(**metadata),
                    arguments=schema_obj,
                ),
            )

        @override
        def make_cronjob(
            self,
            template_args: Json,
            schedule: CronExpression,
        ) -> V1CronJob:
            validated_args: ArgumentType = argument_type.model_validate(template_args)  # type: ignore

            these_annotations = {
                "template_id": template_id,
                "template_args": json.dumps(template_args),
            }

            if annotations is None:
                pass
            elif isinstance(annotations, dict):
                these_annotations.update(annotations)
            else:
                these_annotations.update(annotations(validated_args))

            cronjob = V1CronJob(
                api_version="batch/v1",
                kind="CronJob",
                metadata=V1ObjectMeta(
                    annotations=these_annotations,
                ),
                spec=V1CronJobSpec(
                    schedule=schedule,
                    job_template=V1JobTemplateSpec(
                        spec=V1JobSpec(
                            template=V1PodTemplateSpec(
                                spec=V1PodSpec(
                                    containers=containers(validated_args),
                                    restart_policy="OnFailure",
                                ),
                            ),
                        ),
                    ),
                ),
            )

            return cronjob

    return SimpleCronjobTemplate


def src_to_data_url(src: str) -> str:
    return f"data:text/plain;base64,{base64.b64encode(src.encode('utf-8')).decode('ascii')}"
