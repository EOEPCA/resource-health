from abc import ABC, ABCMeta, abstractmethod
import importlib.util
import json
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_env_var import V1EnvVar
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from kubernetes_asyncio.client.models.v1_volume_mount import V1VolumeMount
from kubernetes_asyncio.client.models.v1_volume import V1Volume
from kubernetes_asyncio.client.models.v1_secret_volume_source import V1SecretVolumeSource
import os
from pydantic import TypeAdapter
import uuid

from api_interface import (
    Json,
)
from check_backends.check_backend import (
    Check,
    CheckId,
    CheckTemplate,
    CheckTemplateId,
    CronExpression,
)
from check_backends.k8s_backend.class_modifier import ClassModifier


# Factory class for loading and storing template classes from Python modules
class TemplateFactory:
    _registry = {}

    @classmethod
    def register_template(cls, template_id: CheckTemplateId, template_class):
        cls._registry[template_id] = template_class

    @classmethod
    def list_templates(cls):
        return list(cls._registry.keys())

    @classmethod
    def get_template(cls, template_id: CheckTemplateId):
        template_class = cls._registry.get(template_id)
        if template_class:
            return template_class()
        else:
            return None

    @classmethod
    def load_templates_from_directory(cls, directory: str):
        """Dynamically load all template modules in a given directory."""
        for filename in os.listdir(directory):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]  # Strip '.py' extension
                cls.load_template_module(directory, module_name)

    @classmethod
    def load_template_module(cls, directory: str, module_name: str):
        """Load a specific module and register its classes."""
        module_path = os.path.join(directory, module_name + '.py')
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)


# Helper functions for adding metadata and telemetry properties to cronjobs
def _add_metadata(cronjob: V1CronJob, template_id: CheckTemplateId, template_args: Json):
    if cronjob.metadata is None:
        cronjob.metadata = V1ObjectMeta()
    cronjob.metadata.annotations["template_id"] = template_id
    cronjob.metadata.annotations["template_args"] = json.dumps(template_args)
    check_id = CheckId(str(uuid.uuid4()))
    cronjob.metadata.name = check_id


def _add_otel_resource_attributes(cronjob: V1CronJob, template_args: Json):
    check_id = cronjob.metadata.name
    user_id = "Health BB user"
    health_check_name = TypeAdapter(str).validate_python(
        template_args["health_check.name"]
    )

    env = cronjob.spec.job_template.spec.template.spec.containers[0].env or []
    if user_id and health_check_name:
        OTEL_RESOURCE_ATTRIBUTES = (
            f"k8s.cronjob.name={check_id},"
            f"user.id={user_id},"
            f"health_check.name={health_check_name}"
        )

        env.append(
            V1EnvVar(
                name="OTEL_RESOURCE_ATTRIBUTES",
                value=OTEL_RESOURCE_ATTRIBUTES,
            )
        )
    cronjob.spec.job_template.spec.template.spec.containers[0].env = env

def _add_otel_exporter_variables(cronjob: V1CronJob):
    env = cronjob.spec.job_template.spec.template.spec.containers[0].env or []
    volumes = cronjob.spec.job_template.spec.template.spec.containers[0].volume_mounts or []
    volume_mounts = cronjob.spec.job_template.spec.template.spec.volumes or []
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        env.append(
            V1EnvVar(
                name="OTEL_EXPORTER_OTLP_ENDPOINT",
                value=os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"]
            )
        )
    if os.environ.get("CHECK_MANAGER_COLLECTOR_TLS_SECRET"):
        env.append(
            V1EnvVar(
                name="OTEL_EXPORTER_OTLP_CERTIFICATE",
                value="/tls/ca.crt"
            )
        )
        env.append(
            V1EnvVar(
                name="OTEL_EXPORTER_OTLP_CLIENT_KEY",
                value="/tls/tls.key"
            )
        )
        env.append(
            V1EnvVar(
                name="OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE",
                value="/tls/tls.crt"
            )
        )
        volume_mounts.append(
            V1VolumeMount(
                name="tls",
                mount_path="/tls",
                read_only=True
            )
        )
        volumes.append(
            V1Volume(
                name="tls",
                secret=V1SecretVolumeSource(
                    secret_name=os.environ["CHECK_MANAGER_COLLECTOR_TLS_SECRET"]
                )
            )
        )
    cronjob.spec.job_template.spec.template.spec.containers[0].env = env
    cronjob.spec.job_template.spec.template.spec.containers[0].volume_mounts = volume_mounts
    cronjob.spec.job_template.spec.template.spec.volumes = volumes


def tag_cronjob(cls, cronjob: V1CronJob, *args, **kwargs):
    tempalte_id = cls.get_check_template().id
    template_args = kwargs.get("template_args") or args[0]

    _add_metadata(cronjob, tempalte_id, template_args)

    _add_otel_resource_attributes(cronjob, template_args)

    _add_otel_exporter_variables(cronjob)

    return cronjob


def make_check(cronjob: V1CronJob):
    template_id = cronjob.metadata.annotations.get("template_id")
    template_args = json.loads(cronjob.metadata.annotations.get("template_args", "{}")) 
    return Check(
        id=CheckId(cronjob.metadata.name),
        metadata={"template_id": template_id, "template_args": template_args},
        schedule=CronExpression(cronjob.spec.schedule),
        outcome_filter={"resource_attributes": {"k8s.cronjob.name": cronjob.metadata.name}},
    )


# Metaclass that gives concrete template classes the ability to automatically
# register a modified version of themselves into the TemplateFactory.
# The modifications add the neccessary methods for the K8sBackend as well
# as properties for generating accessible telemetry.
class TemplateMeta(ABCMeta):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        # Only register concrete classes
        if not cls.__abstractmethods__:
            ModifiedTemplate = ClassModifier(
                cls,
                new_classmethods={"make_check": make_check},
                return_modifications={"make_cronjob": tag_cronjob},
            )
            # Register a modified version of the concrete template class
            TemplateFactory.register_template(
                cls.get_check_template().id,
                ModifiedTemplate,
            )


# Abstract base class for cronjob templates
class CronjobTemplate(ABC, metaclass=TemplateMeta):
    @classmethod
    @abstractmethod
    def get_check_template(cls) -> CheckTemplate:
        """
        Returns an instance of CheckTemplate containng a general information
        about the template and a JSON-schema describing the arguments it accepts.
        """

    @classmethod
    @abstractmethod
    def make_cronjob(
        cls,
        template_args: Json,
        schedule: CronExpression,
    ) -> V1CronJob:
        """ Returns a cronjob from the arguments and schedule. """
