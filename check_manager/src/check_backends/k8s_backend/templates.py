from abc import ABC, abstractmethod
import inspect
import json
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_env_var import V1EnvVar
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from kubernetes_asyncio.client.models.v1_volume_mount import V1VolumeMount
from kubernetes_asyncio.client.models.v1_volume import V1Volume
from kubernetes_asyncio.client.models.v1_secret_volume_source import (
    V1SecretVolumeSource,
)
import logging
import os
import pathlib
from pydantic import TypeAdapter
from typing import Any, Protocol, runtime_checkable
import uuid

from api_utils.json_api_types import Json
from check_backends.check_backend import (
    CheckId,
    CheckTemplate,
    CheckTemplateId,
    CronExpression,
    InCheckMetadata,
    OutCheck,
    OutCheckAttributes,
    OutCheckMetadata,
    OutcomeFilter,
)
from plugin_utils.loader import load_plugins

logger = logging.getLogger("HEALTH_CHECK")


# Protocol class for cronjob templates
@runtime_checkable
class CronjobTemplateProtocol(Protocol):
    def get_check_template(self) -> CheckTemplate:
        pass

    def make_cronjob(
        self,
        template_args: Json,
        schedule: CronExpression,
        userinfo: dict[str, Any],
    ) -> V1CronJob:
        pass


# Optional abstract base class for cronjob templates
class CronjobTemplate(ABC):
    @abstractmethod
    def get_check_template(self) -> CheckTemplate:
        """
        Returns an instance of CheckTemplate containing a general information
        about the template and a JSON-schema describing the arguments it accepts.
        """

    @abstractmethod
    def make_cronjob(
        self,
        template_args: Json,
        schedule: CronExpression,
        userinfo: dict[str, Any],
    ) -> V1CronJob:
        """Returns a cronjob from the arguments and schedule."""


# Helper functions for adding metadata and telemetry properties to cronjobs
def _add_metadata(cronjob: V1CronJob, metadata: InCheckMetadata) -> None:
    if cronjob.metadata is None:
        cronjob.metadata = V1ObjectMeta()
    cronjob.metadata.annotations["name"] = metadata.name
    cronjob.metadata.annotations["description"] = metadata.description
    cronjob.metadata.annotations["template_id"] = metadata.template_id
    cronjob.metadata.annotations["template_args"] = json.dumps(
        metadata.template_args
    )
    cronjob.metadata.name = CheckId(str(uuid.uuid4()))


def _add_otel_resource_attributes(
    cronjob: V1CronJob,
    userinfo: dict[str, Any],
) -> None:
    check_id = cronjob.metadata.name
    username = userinfo.get("username", "Unkown user")
    name = cronjob.metadata.annotations["name"]

    env = cronjob.spec.job_template.spec.template.spec.containers[0].env or []
    OTEL_RESOURCE_ATTRIBUTES = (
        f"k8s.cronjob.name={check_id},"
        f"user.id={username},"
        f"health_check.name={name}"
    )

    env.append(
        V1EnvVar(
            name="OTEL_RESOURCE_ATTRIBUTES",
            value=OTEL_RESOURCE_ATTRIBUTES,
        )
    )
    cronjob.spec.job_template.spec.template.spec.containers[0].env = env


def _add_otel_exporter_variables(cronjob: V1CronJob) -> None:
    env = cronjob.spec.job_template.spec.template.spec.containers[0].env or []
    volumes = (
        cronjob.spec.job_template.spec.template.spec.containers[0].volume_mounts or []
    )
    volume_mounts = cronjob.spec.job_template.spec.template.spec.volumes or []
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        env.append(
            V1EnvVar(
                name="OTEL_EXPORTER_OTLP_ENDPOINT",
                value=os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"],
            )
        )
    if os.environ.get("CHECK_MANAGER_COLLECTOR_TLS_SECRET"):
        env.append(V1EnvVar(name="OTEL_EXPORTER_OTLP_CERTIFICATE", value="/tls/ca.crt"))
        env.append(V1EnvVar(name="OTEL_EXPORTER_OTLP_CLIENT_KEY", value="/tls/tls.key"))
        env.append(
            V1EnvVar(name="OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE", value="/tls/tls.crt")
        )
        volume_mounts.append(
            V1VolumeMount(name="tls", mount_path="/tls", read_only=True)
        )
        volumes.append(
            V1Volume(
                name="tls",
                secret=V1SecretVolumeSource(
                    secret_name=os.environ["CHECK_MANAGER_COLLECTOR_TLS_SECRET"]
                ),
            )
        )
    cronjob.spec.job_template.spec.template.spec.containers[0].env = env
    cronjob.spec.job_template.spec.template.spec.containers[
        0
    ].volume_mounts = volume_mounts
    cronjob.spec.job_template.spec.template.spec.volumes = volumes


def _tag_cronjob(
    cronjob: V1CronJob,
    metadata: InCheckMetadata,
    userinfo: dict[str, Any],
) -> V1CronJob:
    _add_metadata(cronjob, metadata)

    _add_otel_resource_attributes(cronjob, userinfo)

    _add_otel_exporter_variables(cronjob)

    return cronjob


def _make_check(cronjob: V1CronJob) -> OutCheck:
    name = cronjob.metadata.annotations.get("name")
    description = cronjob.metadata.annotations.get("description")
    template_id = cronjob.metadata.annotations.get("template_id")
    template_args = json.loads(cronjob.metadata.annotations.get("template_args", "{}"))
    return OutCheck(
        id=CheckId(cronjob.metadata.name),
        attributes=OutCheckAttributes(
            metadata=OutCheckMetadata(
                name=name,
                description=description,
                template_id=template_id,
                template_args=template_args,
            ),
            schedule=CronExpression(cronjob.spec.schedule),
            outcome_filter=OutcomeFilter(
                resource_attributes={"k8s.cronjob.name": cronjob.metadata.name}
            ),
        ),
    )


def default_make_check(cronjob: V1CronJob) -> OutCheck:
    name: str | None = None
    description: str | None = None
    template_id: CheckTemplateId | None = None
    template_args: dict = {}
    if cronjob.metadata and cronjob.metadata.annotations:
        name = cronjob.metadata.annotations.get("name")
        description = cronjob.metadata.annotations.get("description")
        template_id = cronjob.metadata.annotations.get("template_id")
        template_args = json.loads(
            cronjob.metadata.annotations.get("template_args", "{}")
        )
    cronjob_name: str = (
        cronjob.metadata.name if cronjob.metadata and cronjob.metadata.name
        else ""
    )
    return OutCheck(
        id=CheckId(cronjob_name),
        attributes=OutCheckAttributes(
            metadata=OutCheckMetadata(
                name=name,
                description=description,
                template_id=template_id,
                template_args=template_args,
            ),
            schedule=CronExpression(cronjob.spec.schedule),
            outcome_filter=OutcomeFilter(
                resource_attributes={"k8s.cronjob.name": cronjob_name}
            ),
        ),
    )


class CronjobMaker:
    def __init__(self, cronjob_template: CronjobTemplateProtocol) -> None:
        self.cronjob_template: CronjobTemplateProtocol = cronjob_template

    def get_check_template(self) -> CheckTemplate:
        return self.cronjob_template.get_check_template()

    def make_cronjob(
        self,
        metadata: InCheckMetadata,
        schedule: CronExpression,
        userinfo: dict[str, Any],
    ) -> V1CronJob:
        cronjob = self.cronjob_template.make_cronjob(
            metadata.template_args,
            schedule,
            userinfo,
        )
        return _tag_cronjob(cronjob, metadata, userinfo)

    def make_check(self, cronjob: V1CronJob) -> OutCheck:
        return _make_check(cronjob)


def make_template_value(obj: Any) -> CronjobMaker | None:
    if not inspect.isclass(obj):
        return None
    if not (
        issubclass(obj, CronjobTemplateProtocol)
        and obj != CronjobTemplateProtocol
        and not inspect.isabstract(obj)
    ):
        if issubclass(obj, CronjobTemplate) and obj != CronjobTemplate:
            logger.warning(
                f"Encountered unfinished implementation of CronjobTemplate: {str(obj)}"
            )
        return None

    cronjob_template: CronjobTemplateProtocol = obj()

    return CronjobMaker(cronjob_template)


def load_templates(dirs: str | list[str]) -> dict[str, CronjobMaker]:
    paths: list[str] = [dirs] if isinstance(dirs, str) else dirs
    templates: dict[str, Any] = {}
    for path in paths:
        templates.update(
            load_plugins(
                pathlib.Path(path),
                key=(lambda c: c().get_check_template().id),
                value=make_template_value,
                logger=logger,
            )
        )
    return templates
