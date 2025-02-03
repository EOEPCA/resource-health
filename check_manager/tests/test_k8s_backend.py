import json
import unittest
from unittest.mock import AsyncMock, patch

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_cron_job_spec import V1CronJobSpec
from kubernetes_asyncio.client.models.v1_job_list import V1JobList
from kubernetes_asyncio.client.models.v1_job_template_spec import V1JobTemplateSpec
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from kubernetes_asyncio.client.rest import ApiException
import pytest

from check_backends.k8s_backend import K8sBackend
from check_backends.k8s_backend.templates import TemplateFactory
from check_backends.check_backend import (
    AuthenticationObject,
    Check,
    CheckBackend,
    CheckId,
    CheckTemplate,
    CheckTemplateId,
    CronExpression,
)

NAMESPACE: str = "resource-health"
test_auth = "test-auth"
template_id = "simple_ping"
template_args = {
    "health_check.name": "test-check",
    "endpoint": "www.example.com"
}
schedule = "* * * * *"

cronjob_name = "test-cronjob"
cronjob = V1CronJob(
    metadata=V1ObjectMeta(
        name=cronjob_name,
        annotations={
            "template_id": template_id,
            "template_args": json.dumps(template_args),
        },
    ),
    spec=V1CronJobSpec(
        schedule=str(schedule),
        job_template=V1JobTemplateSpec(),
    )
)


@pytest.fixture
def make_test_check():
    cronjob_name = "test-cronjob"
    return Check(
        id=CheckTemplateId(cronjob_name),
        metadata={
            "template_id": "simple_ping",
            "template_args": {
                "health_check.name": "test-check",
                "endpoint": "www.example.com",
            },
        },
        schedule=CronExpression(schedule),
        outcome_filter={
            "resource_attributes": {
                "k8s.cronjob.name": cronjob_name,
            },
        },
    )


class TestK8sBackend(unittest.IsolatedAsyncioTestCase):
    async def test_list_check_templates(self):
        k8s_backend = K8sBackend(["templates"])
        template_async_iterator = k8s_backend.list_check_templates()
        template_list = []
        async for template in template_async_iterator:
            template_list.append(str(template.id))

        assert template_list == ["default_k8s_template", "simple_ping"]

    @patch("test_k8s_backend.ApiClient", new_callable=AsyncMock)
    @patch("test_k8s_backend.client.BatchV1Api")
    async def test_new_check(self, mock_batch_v1_api, mock_api_client):
        mock_batch_v1_api.return_value.create_namespaced_cron_job = AsyncMock(return_value=cronjob)

        k8s_backend = K8sBackend(
            template_dirs=["templates"],
            api_client=mock_api_client,
        )

        result = await k8s_backend.new_check(
                AuthenticationObject(test_auth),
                CheckTemplateId(template_id),
                template_args,
                CronExpression(schedule),
        )

        self.assertEqual(result.id, cronjob_name)
        self.assertEqual(result.metadata["template_id"], template_id)
        self.assertEqual(result.metadata["template_args"], template_args)
        self.assertEqual(result.schedule, CronExpression(schedule))

        mock_batch_v1_api.return_value.create_namespaced_cron_job.assert_called_once()
        call_kwargs = mock_batch_v1_api.return_value.create_namespaced_cron_job.call_args.kwargs
        self.assertEqual(call_kwargs["namespace"], NAMESPACE)

    @patch("test_k8s_backend.ApiClient", new_callable=AsyncMock)
    @patch("test_k8s_backend.client.BatchV1Api")
    async def test_remove_check(self, mock_batch_v1_api, mock_api_client):
        mock_batch_v1_api.return_value.delete_namespaced_cron_job = AsyncMock(return_value=None)

        k8s_backend = K8sBackend(
            template_dirs=["templates"],
            api_client=mock_api_client,
        )

        result = await k8s_backend.remove_check(
                AuthenticationObject(test_auth),
                CheckId(cronjob_name),
        )

        self.assertEqual(result, None)

        mock_batch_v1_api.return_value.delete_namespaced_cron_job.assert_called_once()
        call_kwargs = mock_batch_v1_api.return_value.delete_namespaced_cron_job.call_args.kwargs
        self.assertEqual(call_kwargs["name"], cronjob_name)
        self.assertEqual(call_kwargs["namespace"], NAMESPACE)

    @patch("test_k8s_backend.ApiClient", new_callable=AsyncMock)
    @patch("test_k8s_backend.client.BatchV1Api")
    async def test_list_checks(self, mock_batch_v1_api, mock_api_client):
        mock_batch_v1_api.return_value.list_namespaced_cron_job = AsyncMock(return_value=V1JobList(items=[cronjob]))

        k8s_backend = K8sBackend(
            template_dirs=["templates"],
            api_client=mock_api_client,
        )

        check_async_iterator = k8s_backend.list_checks(
                AuthenticationObject(test_auth),
                CheckId(cronjob_name),
        )
        check_list = []
        async for check in check_async_iterator:
            check_list.append(check)

        self.assertEqual(len(check_list), 1)
        self.assertEqual(check_list[0].id, cronjob_name)
        self.assertEqual(check_list[0].metadata["template_id"], template_id)
        self.assertEqual(check_list[0].metadata["template_args"], template_args)
        self.assertEqual(check_list[0].schedule, CronExpression(schedule))

        mock_batch_v1_api.return_value.list_namespaced_cron_job.assert_called_once()
        call_args = mock_batch_v1_api.return_value.list_namespaced_cron_job.call_args.args
        self.assertEqual(call_args[0], NAMESPACE)
