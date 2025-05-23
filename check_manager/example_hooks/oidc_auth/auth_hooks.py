import check_hooks.hook_utils as hu

from eoepca_security import OIDCProxyScheme, Tokens
from typing import TypedDict
import os


class UserInfo(TypedDict):
    userid: str
    username: str
    access_token: str
    refresh_token: str | None


def get_fastapi_security() -> OIDCProxyScheme:
    return OIDCProxyScheme(
        openIdConnectUrl=os.environ["OPEN_ID_CONNECT_URL"],
        audience=os.environ["OPEN_ID_CONNECT_AUDIENCE"],
        id_token_header="x-id-token",
        refresh_token_header="x-refresh-token",
        auth_token_header="Authorization",
        auth_token_in_authorization=True,
        auto_error=True,  ## Set False to allow unauthenticated access!
        scheme_name="OIDC behind auth proxy",
    )


def on_auth(tokens: Tokens | None) -> UserInfo:
    print("ON AUTH")

    if tokens is None or tokens["auth"] is None:  # or tokens['id'] is None:
        raise hu.APIException(
            hu.Error(
                status="403",
                code="MissingTokens",
                title="Missing authentication or ID token",
                detail="Potentially missing authenticating proxy",
            )
        )

    claims = {}
    claims.update(tokens["auth"].decoded["payload"])
    if tokens["id"] is not None:
        claims.update(tokens["id"].decoded)

    user_id_claim = os.environ.get("RH_CHECK_USER_ID_CLAIM") or "sub"
    username_claim = os.environ.get("RH_CHECK_USERNAME_CLAIM") or "preferred_username"

    user_id = claims.get(user_id_claim)
    username = claims.get(username_claim)

    if user_id is None or username is None:
        print(claims)
        raise hu.APIException(
            hu.Error(
                status="401",
                code="Missing user id/name",
                title="Missing user identification",
                detail="Username or user id missing",
            )
        )

    return UserInfo(
        userid=user_id,
        username=username,
        access_token=tokens["auth"].raw,
        refresh_token=tokens["refresh"].raw if tokens["refresh"] else None,
    )


def on_template_access(userinfo: UserInfo, template: hu.CheckTemplate) -> bool:
    print("ON TEMPLATE_ACCESS")

    if template.id == "default_k8s_template" and userinfo["username"] != "bob":
        return False

    return True


def on_check_create(userinfo: UserInfo, check: hu.InCheckAttributes) -> bool:
    print("ON CHECK CREATE")

    if userinfo["username"] not in ["alice", "bob"]:
        return False

    return True


def on_check_remove(userinfo: UserInfo, check: hu.OutCheck) -> bool:
    print("ON CHECK REMOVE")

    if userinfo["username"] not in ["alice", "bob"]:
        return False

    return True


def on_check_access(userinfo: UserInfo, check: hu.OutCheck) -> bool:
    print("ON CHECK ACCESS")

    return True


def on_check_run(userinfo: UserInfo, check: hu.OutCheck) -> bool:
    print("ON CHECK RUN")

    return True


## For the k8s backend


async def get_k8s_config(userinfo: UserInfo) -> hu.K8sConfiguration:
    ## Using kube[ctl] config
    print("get_k8s_config: Using local kube config file")
    return await hu.k8s_config_from_file(
        # config_file="~/.kube/config",
        context=os.environ.get("RH_CHECK_KUBE_CONTEXT"),
    )
    ## Using cluster mounted credentials
    # return await k8s_config_from_cluster()


def get_k8s_namespace(userinfo: UserInfo) -> str:
    return "resource-health"


async def on_k8s_cronjob_access(
    userinfo: UserInfo, client: hu.K8sClient, cronjob: hu.K8sCronJob
) -> bool:
    print("on_k8s_cronjob_access")

    return cronjob.metadata.annotations.get("owner") == userinfo["username"]


async def on_k8s_cronjob_create(
    userinfo: UserInfo, client: hu.K8sClient, cronjob: hu.K8sCronJob
) -> bool:
    print("on_k8s_cronjob_create")

    ## Ensure cronjob is tagged with correct owner

    if (
        "owner" in cronjob.metadata.annotations
        and cronjob.metadata.annotations["owner"] != userinfo["username"]
    ):
        return False

    cronjob.metadata.annotations["owner"] = userinfo["username"]

    ## Ensure the user has an offline token set
    ## Note: Would be more robust to check on every access but use a cache
    secret_name = f"resource-health-{userinfo['username']}-offline-secret"
    secret_namespace = get_k8s_namespace(userinfo)

    offline_secret = await hu.lookup_k8s_secret(
        client=client,
        namespace=secret_namespace,
        name=secret_name
    )

    if offline_secret is None:
        if userinfo['refresh_token'] is None:
            raise hu.APIException(hu.Error(
                status="404",
                code="MissingOfflineToken",
                title="Missing offline token, please create at least one check using the website",
            ))
        await hu.create_k8s_secret(
            client=client,
            name=secret_name,
            namespace=secret_namespace,
            string_data={
                "offline_token": userinfo['refresh_token']
            }
        )

    return True


def on_k8s_cronjob_remove(
    userinfo: UserInfo, client: hu.K8sClient, cronjob: hu.K8sCronJob
) -> bool:
    print("on_k8s_cronjob_remove")

    ## Access already checked as part of on_k8s_cronjob_access

    return True


def on_k8s_cronjob_run(userinfo: UserInfo, client: hu.K8sClient, cronjob: hu.K8sCronJob) -> bool:
    print("on_k8s_cronjob_run")

    ## Access already checked as part of on_k8s_cronjob_access

    return True


## For the mock backend


def get_mock_username(userinfo: UserInfo) -> str:
    return userinfo["username"]
