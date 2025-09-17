from eoepca_api_utils.exceptions import (
    APIException,  # noqa: F401 used by hooks which import this
    APIForbiddenError,  # noqa: F401 used by hooks which import this
    APIUnauthorizedError,  # noqa: F401 used by hooks which import this
    APIUserInputError,  # noqa: F401 used by hooks which import this
)
import typing
from check_backends.check_backend import (
    CheckTemplate,  # noqa: F401 used by hooks which import this
    CheckId,  # noqa: F401 used by hooks which import this
    InCheckAttributes,  # noqa: F401 used by hooks which import this
    OutCheck,  # noqa: F401 used by hooks which import this
    CheckTemplateIdError,  # noqa: F401 used by hooks which import this
    CheckIdError,  # noqa: F401 used by hooks which import this
)
import os as _os
from kubernetes_asyncio.client.models.v1_cron_job import V1CronJob as K8sCronJob  # noqa: F401 used by hooks which import this
from kubernetes_asyncio.client.api_client import ApiClient as K8sClient
from kubernetes_asyncio.client.models.v1_secret import V1Secret as K8sSecret
from kubernetes_asyncio.client.configuration import Configuration as K8sConfiguration
from kubernetes_asyncio.client.rest import ApiException as K8sApiException
from kubernetes_asyncio.client import CoreV1Api as _CoreV1API
from kubernetes_asyncio.client.models.v1_object_meta import (
    V1ObjectMeta as _V1ObjectMeta,
)
from kubernetes_asyncio.config import (
    load_kube_config as _load_kube_config,
    load_incluster_config as _load_incluster_config,
    KUBE_CONFIG_DEFAULT_LOCATION,
)


def k8s_config(
    *,
    host: str | None = None,
    api_key: str | None = None,
    api_key_prefix: str | None = None,
    username: str | None = None,
    password: str | None = None,
    discard_unknown_keys: bool = False,
    disabled_client_side_validations: str = "",
    server_index: int | None = None,
    server_variables: dict | None = None,
    server_operation_index: dict | None = None,
    server_operation_variables: dict | None = None,
    ssl_ca_cert: str | None = None,
) -> K8sConfiguration:
    return K8sConfiguration(
        host=host,
        api_key=api_key,
        api_key_prefix=api_key_prefix,
        username=username,
        password=password,
        discard_unknown_keys=discard_unknown_keys,
        disabled_client_side_validations=disabled_client_side_validations,
        server_index=server_index,
        server_variables=server_variables,
        server_operation_index=server_operation_index,
        server_operation_variables=server_operation_variables,
        ssl_ca_cert=ssl_ca_cert,
    )


async def k8s_config_from_file(
    config_file: str = KUBE_CONFIG_DEFAULT_LOCATION,
    *,
    context: str | None = None,
    persist_config=True,
    temp_file_path=None,
    ## Config values
    host: str | None = None,
    api_key: str | None = None,
    api_key_prefix: str | None = None,
    username: str | None = None,
    password: str | None = None,
    discard_unknown_keys: bool = False,
    disabled_client_side_validations: str = "",
    server_index: int | None = None,
    server_variables: dict | None = None,
    server_operation_index: dict | None = None,
    server_operation_variables: dict | None = None,
    ssl_ca_cert: str | None = None,
) -> K8sConfiguration:
    cfg = k8s_config(
        host=host,
        api_key=api_key,
        api_key_prefix=api_key_prefix,
        username=username,
        password=password,
        discard_unknown_keys=discard_unknown_keys,
        disabled_client_side_validations=disabled_client_side_validations,
        server_index=server_index,
        server_variables=server_variables,
        server_operation_index=server_operation_index,
        server_operation_variables=server_operation_variables,
        ssl_ca_cert=ssl_ca_cert,
    )

    await _load_kube_config(
        config_file=config_file,
        context=context,
        client_configuration=cfg,
        persist_config=persist_config,
        temp_file_path=temp_file_path,
    )

    return cfg


# client_configuration=None


async def k8s_config_from_cluster(
    *,
    token_filename: str | None = None,
    cert_filename: str | None = None,
    try_refresh_token: bool = True,
    environ: typing.Any = _os.environ,
    ## Config values
    host: str | None = None,
    api_key: str | None = None,
    api_key_prefix: str | None = None,
    username: str | None = None,
    password: str | None = None,
    discard_unknown_keys: bool = False,
    disabled_client_side_validations: str = "",
    server_index: int | None = None,
    server_variables: dict | None = None,
    server_operation_index: dict | None = None,
    server_operation_variables: dict | None = None,
    ssl_ca_cert: str | None = None,
) -> K8sConfiguration:
    cfg = k8s_config(
        host=host,
        api_key=api_key,
        api_key_prefix=api_key_prefix,
        username=username,
        password=password,
        discard_unknown_keys=discard_unknown_keys,
        disabled_client_side_validations=disabled_client_side_validations,
        server_index=server_index,
        server_variables=server_variables,
        server_operation_index=server_operation_index,
        server_operation_variables=server_operation_variables,
        ssl_ca_cert=ssl_ca_cert,
    )

    args = {
        "client_configuration": cfg,
        "try_refresh_token": try_refresh_token,
        "environ": environ,
    }

    if token_filename is not None:
        args["token_filename"] = token_filename

    if cert_filename is not None:
        args["cert_filename"] = cert_filename

    _load_incluster_config(**args)

    return cfg


async def lookup_k8s_secret(
    client: K8sClient,
    namespace: str,
    name: str,
) -> K8sSecret | None:
    api_instance = _CoreV1API(client)
    try:
        api_response = await api_instance.read_namespaced_secret(
            namespace=namespace,
            name=name,
        )
    except K8sApiException as e:
        if e.status == 404:
            return None
        else:
            raise e
    except Exception as e:
        raise e

    assert isinstance(api_response, K8sSecret)
    return api_response


async def create_k8s_secret(
    client: K8sClient,
    name: str,
    namespace: str,
    string_data: dict[str, str],
) -> K8sSecret:
    api_instance = _CoreV1API(client)

    api_response = await api_instance.create_namespaced_secret(
        namespace=namespace,
        body=K8sSecret(
            metadata=_V1ObjectMeta(name=name),
            string_data=string_data,
        ),
    )

    assert isinstance(api_response, K8sSecret)
    return api_response
