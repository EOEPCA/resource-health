from typing import Optional, override, Generic, TypeVar, Any, Callable
import json
from abc import abstractmethod

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

DEFAULT_CONTAINER_IMAGE: str = "docker.io/eoepca/healthcheck_runner:2.0.0-beta2"


def make_base_cronjob(
    schedule: CronExpression,
    container_image: Optional[str] = DEFAULT_CONTAINER_IMAGE,
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
    image : str,
    *,
    name : str = "healthcheck",
    env : dict[str, str]|None = None,
    args : list[str]|None = None,
    command : list[str]|None = None,
    image_pull_policy : str|None = "IfNotPresent"
) -> V1Container:
    return V1Container(
        name = name,
        image = image,
        args=args,
        command=command,
        env=[
            V1EnvVar(
                name=name,
                value=value
            )
            for name,value in (env or {}).items()
        ],
        image_pull_policy=image_pull_policy
    )
        
    # env.append(
    #     V1EnvVar(
    #         name="RESOURCE_HEALTH_RUNNER_SCRIPT",
    #         value="data:text/plain;base64,ZnJvbSBvcyBpbXBvcnQgZW52aXJvbgppbXBvcnQgcmVxdWVzdHMKCkdFTkVSSUNfRU5EUE9JTlQ6IHN0ciA9IGVudmlyb25bIkdFTkVSSUNfRU5EUE9JTlQiXQpFWFBFQ1RFRF9TVEFUVVNfQ09ERTogaW50ID0gaW50KGVudmlyb25bIkVYUEVDVEVEX1NUQVRVU19DT0RFIl0pCgoKZGVmIHRlc3RfcGluZygpIC0+IE5vbmU6CiAgICByZXNwb25zZSA9IHJlcXVlc3RzLmdldCgKICAgICAgICBHRU5FUklDX0VORFBPSU5ULAogICAgKQogICAgYXNzZXJ0IHJlc3BvbnNlLnN0YXR1c19jb2RlID09IEVYUEVDVEVEX1NUQVRVU19DT0RFCg==",
    #     )
    # )
    # env.append(
    #     V1EnvVar(
    #         name="GENERIC_ENDPOINT",
    #         value=endpoint,
    #     )
    # )
    # env.append(
    #     V1EnvVar(
    #         name="EXPECTED_STATUS_CODE",
    #         value=expected_status_code,
    #     )
    # )

ArgumentType = TypeVar("ArgumentType", bound=pydantic.BaseModel)

def cronjob_template[ArgumentType](
    template_id : str,
    argument_type : type[ArgumentType],
    *,
    label : str|None = None,
    description : str|None = None,
    template_metadata : dict[str,str]|None = None,
    annotations : Callable[[ArgumentType], dict[str, str]]|dict[str, str]|None = None,
    containers : Callable[[ArgumentType], list[V1Container]]
) -> type[CronjobTemplate]:
    class SimpleCronjobTemplate(CronjobTemplate):
        @override
        def get_check_template(self) -> CheckTemplate:
            if template_metadata is not None:
                metadata : dict[str, str] = template_metadata.copy()
            else:
                metadata = {}
            
            if label is not None:
                metadata['label'] = label
            if description is not None:
                metadata['description'] = description

            schema_obj : dict[str, Any] = argument_type.model_json_schema() # type: ignore
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
            validated_args : ArgumentType = argument_type.model_validate(template_args) # type: ignore

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