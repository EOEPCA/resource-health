from typing import Optional

from kubernetes_asyncio.client.models.v1_container import V1Container
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_cron_job_spec import V1CronJobSpec
from kubernetes_asyncio.client.models.v1_env_var import V1EnvVar
from kubernetes_asyncio.client.models.v1_env_var_source import V1EnvVarSource
from kubernetes_asyncio.client.models.v1_job_spec import V1JobSpec
from kubernetes_asyncio.client.models.v1_pod_spec import V1PodSpec
from kubernetes_asyncio.client.models.v1_job_template_spec import V1JobTemplateSpec
from kubernetes_asyncio.client.models.v1_pod_template_spec import V1PodTemplateSpec
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from kubernetes_asyncio.client.models.v1_secret_key_selector import V1SecretKeySelector

from ..templates import CronExpression

DEFAULT_CONTAINER_IMAGE: str = "docker.io/eoepca/healthcheck_runner:v0.3.0-internal5"
DEFAULT_SIDECAR_IMAGE: str = "docker.io/eoepca/mitmproxy_oidc:v0.3.0-internal2"


def make_base_cronjob(
    schedule: CronExpression,
    container_image: str = DEFAULT_CONTAINER_IMAGE,
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
                            restart_policy="Never",
                        ),
                    ),
                ),
            ),
        ),
    )


def make_sidecar_container(
    username: str,
    container_image: str = DEFAULT_SIDECAR_IMAGE,
) -> V1Container:
    return V1Container(
        name="proxy-oidc-sidecar",
        image=container_image,
        image_pull_policy="IfNotPresent",
        env=[
            V1EnvVar(
                name="OPEN_ID_CONNECT_URL",
                value=(
                    "https://iam-auth.develop.eoepca.org/realms/"
                    "eoepca/.well-known/openid-configuration"
                ),
            ),
            V1EnvVar(
                name="OPEN_ID_REFRESH_TOKEN",
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(
                        name=f"resource-health-{username}-offline-secret",
                        key="offline_token",
                    ),
                ),
            ),
            V1EnvVar(
                name="OPEN_ID_CONNECT_CLIENT_ID",
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(
                        name="resource-health-iam-client-credentials",
                        key="client_id",
                    ),
                ),
            ),
            V1EnvVar(
                name="OPEN_ID_CONNECT_CLIENT_SECRET",
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(
                        name="resource-health-iam-client-credentials",
                        key="client_secret",
                    ),
                ),
            ),
            V1EnvVar(
                name="OPEN_ID_CONNECT_AUDIENCE",
                value="account",
            ),
            V1EnvVar(
                name="REMOTE_PROTECTED_DOMAIN",
                value="https://opensearch-cluster-master-headless:9200",
            ),
            V1EnvVar(
                name="TLS_NO_VERIFY",
                value="true",
            ),
        ],
    )
