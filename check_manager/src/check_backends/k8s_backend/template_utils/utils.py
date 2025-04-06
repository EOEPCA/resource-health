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
from kubernetes_asyncio.client.models.v1_volume_mount import V1VolumeMount

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
    or "docker.io/eoepca/healthcheck_runner:v0.3.0-internal5"
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
    volume_mounts: dict[str,str] | None = None,
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
        volume_mounts=[
            V1VolumeMount(name=key, mount_path=value)
            for key,value in (volume_mounts or {}).items()
        ]
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
    resource_attributes: dict[str,str] | None = None,
    volume_mounts: dict[str,str] | None = None,
) -> V1Container:
    if env is None:
        env = {}
    else:
        env = env.copy()

    env["RESOURCE_HEALTH_RUNNER_SCRIPT"] = script_url
    if requirements_url is not None:
        env["RESOURCE_HEALTH_RUNNER_REQUIREMENTS"] = requirements_url

    if resource_attributes is not None:
        env["OTEL_RESOURCE_ATTRIBUTES"] = ",".join(
            f"{key}={value}"
            for key,value in resource_attributes.items()
        )

    return container(
        image=image,
        name=name,
        env=env,
        secret_env=secret_env,
        args=args,
        command=command,
        image_pull_policy=image_pull_policy,
        volume_mounts=volume_mounts,
    )


def oidc_mitmproxy_container(
    remote_domain: str,
    *,
    openid_connect_url: str,
    openid_client_id_secret: tuple[str, str],
    openid_client_secret_secret: tuple[str, str],
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
    volume_mounts: dict[str,str] | None = None,
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
    secret_env["OPEN_ID_CONNECT_CLIENT_ID"] = openid_client_id_secret
    secret_env["OPEN_ID_CONNECT_CLIENT_SECRET"] = openid_client_secret_secret

    return container(
        image=image,
        name=name,
        env=env,
        secret_env=secret_env,
        args=args,
        command=command,
        image_pull_policy=image_pull_policy,
        volume_mounts=volume_mounts,
    )


ArgumentType = TypeVar("ArgumentType", bound=pydantic.BaseModel)


def cronjob_template[ArgumentType](
    template_id: str,
    argument_type: type[ArgumentType],
    *,
    label: str | None = None,
    description: str | None = None,
    template_metadata: dict[str, str] | None = None,
    annotations: Callable[[ArgumentType, Any], dict[str, str]]
    | dict[str, str]
    | None = None,
    containers: Callable[[ArgumentType, Any], list[V1Container]],
    volumes: Callable[[ArgumentType, Any], list[V1Volume]] | list[V1Volume] | None = None,
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
            userinfo: Any
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
                these_annotations.update(annotations(validated_args, userinfo))

            if volumes is None:
                these_volumes : list[V1Volume] = []
            elif isinstance(volumes, list):
                these_volumes = volumes
            else:
                these_volumes = volumes(validated_args, userinfo)

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
                                    containers=containers(validated_args, userinfo),
                                    restart_policy="OnFailure",
                                    volumes=these_volumes
                                ),
                            ),
                        ),
                    ),
                ),
            )

            return cronjob

    return SimpleCronjobTemplate

def simple_runner_template[ArgumentType](
    template_id: str,
    argument_type: type[ArgumentType],
    *,
    label: str | None = None,
    description: str | None = None,
    template_metadata: dict[str, str] | None = None,
    annotations: Callable[[ArgumentType, Any], dict[str, str]]
    | dict[str, str]
    | None = None,
    script_url: Callable[[ArgumentType, Any], str] | str,
    requirements_url: Callable[[ArgumentType, Any], str] | str | None = None,
    runner_env: Callable[[ArgumentType, Any], dict[str, str]] | dict[str,str] | None = None,
    user_id: Callable[[ArgumentType, Any], str] | str | None = None,
    otlp_exporter_endpoint : str | None = None,
    otlp_tls_secret : str | None = None,
    runner_image: str = DEFAULT_RUNNER_IMAGE,
    resource_attributes: dict[str,str]|None = None,
    proxy : bool = False,
    proxy_oidc_client_secret : tuple[str,str,str]|None = None,
    proxy_oidc_refresh_token_secret : Callable[[ArgumentType, Any], tuple[str, str]] | tuple[str,str] | None = None,
    proxy_oidc_url : str|None = os.environ.get("OPEN_ID_CONNECT_URL"),
    proxy_oidc_audience : str = "account",
    proxy_remote_domain : str = "https://opensearch-cluster-master-headless:9200",
    proxy_image : str = DEFAULT_OIDC_MITMPROXY_IMAGE,
) -> type[CronjobTemplate]:
    if proxy:
        if proxy_oidc_url is None:
            raise ValueError("Trying to create CronJob template with proxy requires proxy_oidc_url")
        if proxy_oidc_refresh_token_secret is None:
            raise ValueError("Trying to create CronJob template with proxy requires proxy_oidc_refresh_token_secret")
        if proxy_oidc_client_secret is None:
            raise ValueError("Trying to create CronJob template with proxy requires proxy_oidc_client_secret")

    def template_containers(
        template_args: ArgumentType,
        userinfo: Any,
    ) -> list[V1Container]:
        if isinstance(script_url, str):
            script = script_url
        else:
            script = script_url(template_args, userinfo)
        
        if requirements_url is None:
            requirements = None
        elif isinstance(requirements_url, str):
            requirements = requirements_url
        else:
            requirements = requirements_url(template_args, userinfo)

        if resource_attributes is None:
            these_resource_attributes = {}
        else:
            these_resource_attributes = resource_attributes.copy()

        if user_id is None:
            pass
        elif isinstance(user_id, str):
            these_resource_attributes['user.id'] = user_id
        else:
            these_resource_attributes['user.id'] = user_id(template_args, userinfo)

        if runner_env is None:
            env = {}
        elif isinstance(runner_env, dict):
            env = runner_env.copy()
        else:
            env = runner_env(template_args, userinfo)

        if otlp_exporter_endpoint is None:
            if otlp_tls_secret is None:
                env["OTEL_EXPORTER_OTLP_ENDPOINT"] = 'http://resource-health-opentelemetry-collector:4317'
            else:
                env["OTEL_EXPORTER_OTLP_ENDPOINT"] = 'https://resource-health-opentelemetry-collector:4317'
        else:
            env["OTEL_EXPORTER_OTLP_ENDPOINT"] = otlp_exporter_endpoint

        if otlp_tls_secret is None:
            volume_mounts = None
        else:
            volume_mounts = {
                "otlp-tls": "/tls"
            }
            env["OTEL_EXPORTER_OTLP_CERTIFICATE"] = "/tls/ca.crt"
            env["OTEL_EXPORTER_OTLP_CLIENT_KEY"] = "/tls/tls.key"
            env["OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE"] = "/tls/tls.crt"

        these_containers = [
            runner_container(
                script_url=script,
                requirements_url=requirements,
                resource_attributes=these_resource_attributes,
                volume_mounts=volume_mounts,
                env=env,
                image=runner_image,
                command=None if not proxy else ["/usr/bin/bash"],
                args=None if not proxy else [
                    "-c",
                    "/app/run_script.sh pytest --export-traces -rP --suppress-tests-failed-exit-code tests.py; ret=$?; curl -s 'http://127.0.0.1:8080/quitquitquit'; exit $ret",
                ]
            )
        ]

        if proxy:
            assert(proxy_oidc_refresh_token_secret is not None)
            assert(proxy_oidc_url is not None)
            assert(proxy_oidc_client_secret is not None)

            if isinstance(proxy_oidc_refresh_token_secret, tuple):
                this_proxy_oidc_refresh_token_secret = proxy_oidc_refresh_token_secret
            else:
                this_proxy_oidc_refresh_token_secret = proxy_oidc_refresh_token_secret(template_args, userinfo)
            
            these_containers.append(
                oidc_mitmproxy_container(
                    remote_domain=proxy_remote_domain,
                    openid_connect_url=proxy_oidc_url,
                    openid_client_id_secret = (proxy_oidc_client_secret[0],proxy_oidc_client_secret[1]),
                    openid_client_secret_secret = (proxy_oidc_client_secret[0],proxy_oidc_client_secret[2]),
                    openid_audience = proxy_oidc_audience,
                    refresh_token_secret = this_proxy_oidc_refresh_token_secret,
                    tls_verify = False,
                    image = proxy_image,
                )
            )

        return these_containers

    
    if otlp_tls_secret is None:
        volumes : list[V1Volume] | None = None
    else:
        volumes = [
            V1Volume(name="otlp-tls", secret=V1SecretVolumeSource(
                secret_name=otlp_tls_secret
            ))
        ]

    return cronjob_template(
        template_id = template_id,
        argument_type = argument_type,
        label = label,
        description = description,
        template_metadata = template_metadata,
        annotations = annotations,
        containers=template_containers,
        volumes=volumes,
    )

def src_to_data_url(src: str) -> str:
    return f"data:text/plain;base64,{base64.b64encode(src.encode('utf-8')).decode('ascii')}"
