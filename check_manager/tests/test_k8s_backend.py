import contextlib
import json
import os
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob
from kubernetes_asyncio.client.models.v1_cron_job_spec import V1CronJobSpec
from kubernetes_asyncio.client.models.v1_job_list import V1JobList
from kubernetes_asyncio.client.models.v1_job_template_spec import V1JobTemplateSpec
from kubernetes_asyncio.client.models.v1_object_meta import V1ObjectMeta
from kubernetes_asyncio.client.rest import ApiException
import pytest

from check_backends.k8s_backend import K8sBackend, load_config
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
from exceptions import (
    CheckInternalError,
    CheckTemplateIdError,
    CheckIdError,
    CheckConnectionError,
)

NAMESPACE: str = "resource-health"
TEMPLATES: str = "templates"
test_auth = "test-auth"
template_id = "simple_ping"
bad_template_id = "simply_ping"
template_args = {
    "health_check.name": "test-check",
    "endpoint": "www.example.com"
}
schedule = "* * * * *"

check_id_1 = "check_id_1"
check_id_2 = "check_id_2"
check_id_3 = "check_id_3"
cronjob_1 = V1CronJob(
    metadata=V1ObjectMeta(
        name=check_id_1,
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
cronjob_2 = V1CronJob(
    metadata=V1ObjectMeta(
        name=check_id_2,
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


@patch("test_k8s_backend.ApiClient", new_callable=AsyncMock)
async def test_aclose(mock_api_client):
    try:
        k8s_backend = K8sBackend(
            template_dirs=[TEMPLATES],
            api_client=mock_api_client,
        )
    finally:
        await k8s_backend.aclose()


@pytest.mark.parametrize("kubernetes_service_host", [
    "mock_service_host", None
])
@patch("test_k8s_backend.config.load_kube_config", new_callable=AsyncMock)
@patch("test_k8s_backend.config.load_incluster_config", new_callable=Mock)
async def test_load_config(
    mock_load_incluster_config,
    mock_load_kube_config,
    kubernetes_service_host,
):
    with patch.dict(
        os.environ,
        {"KUBERNETES_SERVICE_HOST": kubernetes_service_host}
        if kubernetes_service_host else {},
        clear=True,
    ):
        await load_config()
        if kubernetes_service_host:
            mock_load_incluster_config.assert_called_once()
            mock_load_kube_config.assert_not_called()
        else:
            mock_load_incluster_config.assert_not_called()
            mock_load_kube_config.assert_called_once()


@pytest.mark.parametrize("template_ids, expected", [
    (["simple_ping"], ["simple_ping"]),
    (["simply_ping"], []),
    (["default_k8s_template", "simply_ping"], ["default_k8s_template"]),
    (None, ["default_k8s_template", "simple_ping"]),
])
@patch("check_backends.k8s_backend.load_config", new_callable=AsyncMock)
@patch("test_k8s_backend.ApiClient", new_callable=AsyncMock)
@patch("test_k8s_backend.client.BatchV1Api")
async def test_list_check_templates(
    mock_batch_v1_api,
    mock_api_client,
    mock_load_config,
    template_ids,
    expected,
):
    k8s_backend = K8sBackend(
        template_dirs=[TEMPLATES],
        api_client=mock_api_client,
    )
    template_async_iterator = k8s_backend.list_check_templates(template_ids)
    template_list = []
    async for template in template_async_iterator:
        template_list.append(str(template.id))

    assert template_list == expected

    mock_load_config.assert_not_called()
    mock_batch_v1_api.assert_not_called()


@pytest.mark.parametrize(
    (
        "template_id,"
        "side_effect,"
        "expectation"
    ),
    [
        (
            "simple_ping",
            None,
            contextlib.nullcontext()
        ),
        (
            "simple_ping",
            ApiException(status=422),
            pytest.raises(CheckInternalError)
        ),
        (
            "simple_ping",
            ApiException(),
            pytest.raises(ApiException)
        ),
        (
            "simple_ping",
            aiohttp.ClientConnectionError(),
            pytest.raises(CheckConnectionError)
        ),
        (
            "simple_ping",
            Exception(),
            pytest.raises(Exception)
        ),
        (
            "simply_ping",
            None,
            pytest.raises(CheckTemplateIdError)
        ),
    ]
)
@patch("check_backends.k8s_backend.load_config", new_callable=AsyncMock)
@patch("test_k8s_backend.ApiClient", new_callable=AsyncMock)
@patch("test_k8s_backend.client.BatchV1Api")
async def test_new_check(
    mock_batch_v1_api,
    mock_api_client,
    mock_load_config,
    template_id,
    side_effect,
    expectation,
):
    mock_batch_v1_api.return_value.create_namespaced_cron_job = AsyncMock(
        side_effect=side_effect,
        return_value=cronjob_1,
    )

    k8s_backend = K8sBackend(
        template_dirs=[TEMPLATES],
        api_client=mock_api_client,
    )

    with expectation:
        result = await k8s_backend.new_check(
            AuthenticationObject(test_auth),
            CheckTemplateId(template_id),
            template_args,
            CronExpression(schedule),
        )

        # assert exc_info is None
        assert result.id == check_id_1
        assert result.metadata["template_id"] == template_id
        assert result.metadata["template_args"] == template_args
        assert result.schedule == CronExpression(schedule)

        mock_load_config.assert_called_once()
        mock_batch_v1_api.assert_called_once()
        mock_batch_v1_api.return_value.create_namespaced_cron_job.assert_called_once()
        call_kwargs = mock_batch_v1_api.return_value.create_namespaced_cron_job.call_args.kwargs
        assert call_kwargs["namespace"] == NAMESPACE


@pytest.mark.parametrize(
    ("side_effect, expectation"),
    [
        (None, contextlib.nullcontext()),
        (ApiException(status=404), pytest.raises(CheckIdError)),
        (ApiException(), pytest.raises(ApiException)),
        (aiohttp.ClientConnectionError(), pytest.raises(CheckConnectionError)),
        (Exception(), pytest.raises(Exception)),
    ]
)
@patch("check_backends.k8s_backend.load_config", new_callable=AsyncMock)
@patch("test_k8s_backend.ApiClient", new_callable=AsyncMock)
@patch("test_k8s_backend.client.BatchV1Api")
async def test_remove_check(
    mock_batch_v1_api,
    mock_api_client,
    mock_load_config,
    side_effect,
    expectation,
):
    mock_batch_v1_api.return_value.delete_namespaced_cron_job = AsyncMock(
        side_effect=side_effect,
    )

    k8s_backend = K8sBackend(
        template_dirs=[TEMPLATES],
        api_client=mock_api_client,
    )

    with expectation:
        result = await k8s_backend.remove_check(
            AuthenticationObject(test_auth),
            CheckId(check_id_1),
        )

        assert result is None

        mock_load_config.assert_called_once()
        mock_batch_v1_api.assert_called_once()
        mock_batch_v1_api.return_value.delete_namespaced_cron_job.assert_called_once()
        call_kwargs = mock_batch_v1_api.return_value.delete_namespaced_cron_job.call_args.kwargs
        assert call_kwargs["name"] == check_id_1
        assert call_kwargs["namespace"] == NAMESPACE


@pytest.mark.parametrize(
    (
        "check_ids,"
        "side_effect,"
        "expectation,"
        "expected"
    ),
    [
        (
            None,
            None,
            contextlib.nullcontext(),
            2,
        ),
        (
            [check_id_1],
            None,
            contextlib.nullcontext(),
            1,
        ),
        (
            [check_id_1, check_id_2],
            None,
            contextlib.nullcontext(),
            2,
        ),
        (
            [check_id_3],
            None,
            contextlib.nullcontext(),
            0,
        ),
        (
            [check_id_1, check_id_3],
            None,
            contextlib.nullcontext(),
            1,
        ),
        (
            None,
            ApiException,
            pytest.raises(ApiException),
            None,
        ),
        (
            None,
            aiohttp.ClientConnectionError,
            pytest.raises(CheckConnectionError),
            None,
        ),
        (
            None,
            Exception,
            pytest.raises(Exception),
            None,
        ),
    ],
)
@patch("check_backends.k8s_backend.load_config", new_callable=AsyncMock)
@patch("test_k8s_backend.ApiClient", new_callable=AsyncMock)
@patch("test_k8s_backend.client.BatchV1Api")
async def test_list_checks(
    mock_batch_v1_api,
    mock_api_client,
    mock_load_config,
    check_ids,
    side_effect,
    expectation,
    expected,
):
    mock_batch_v1_api.return_value.list_namespaced_cron_job = AsyncMock(
        side_effect=side_effect,
        return_value=V1JobList(
            items=[cronjob_1, cronjob_2]
        ),
    )

    k8s_backend = K8sBackend(
        template_dirs=[TEMPLATES],
        api_client=mock_api_client,
    )

    with expectation:
        check_async_iterator = k8s_backend.list_checks(
            AuthenticationObject(test_auth),
            check_ids,
        )
        check_list = []
        async for check in check_async_iterator:
            check_list.append(check)

        assert len(check_list) == expected

        mock_load_config.assert_called_once()
        mock_batch_v1_api.assert_called_once()
        mock_batch_v1_api.return_value.list_namespaced_cron_job.assert_called_once()
        call_args = mock_batch_v1_api.return_value.list_namespaced_cron_job.call_args.args
        assert call_args[0] == NAMESPACE
