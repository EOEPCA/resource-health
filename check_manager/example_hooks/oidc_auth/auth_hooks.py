from fastapi import Request
import check_hooks.hook_utils as hu
from eoepca_security import OIDCProxyScheme, Tokens
from typing import TypedDict
import os
from datetime import datetime, timedelta
from cron_converter import Cron


class UserInfo(TypedDict):
    userid: str
    username: str
    access_token: str
    refresh_token: str | None


oidc_proxy_scheme = OIDCProxyScheme(
    openIdConnectUrl=os.environ["OPEN_ID_CONNECT_URL"],
    audience=os.environ["OPEN_ID_CONNECT_AUDIENCE"],
    id_token_header="x-id-token",
    refresh_token_header="x-refresh-token",
    auth_token_header="Authorization",
    auth_token_in_authorization=True,
    auto_error=True,  ## Set False to allow unauthenticated access!
    scheme_name="OIDC behind auth proxy",
)


async def get_fastapi_security(request: Request) -> Tokens | None:
    return await oidc_proxy_scheme(request)


def on_auth(tokens: Tokens | None) -> UserInfo:
    print("ON AUTH")

    if tokens is None or tokens["auth"] is None:  # or tokens['id'] is None:
        raise hu.APIForbiddenError(
            title="Missing authentication or ID token",
            detail="Potentially missing authenticating proxy",
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
        raise hu.APIUnauthorizedError(
            title="Missing user identification",
            detail="Username or user id missing",
        )

    return UserInfo(
        userid=user_id,
        username=username,
        access_token=tokens["auth"].raw,
        refresh_token=tokens["refresh"].raw if tokens["refresh"] else None,
    )


def on_template_access(userinfo: UserInfo, template: hu.CheckTemplate) -> None:
    print("ON TEMPLATE_ACCESS")

    if template.id == "generic_script_template" and userinfo["username"] != "bob":
        raise hu.CheckTemplateIdError(template.id)


# This is not a hook
def raise_error_if_schedule_too_frequent(
    cron_schedule: str, min_allowed_days_between_runs: int, error_detail: str
) -> None:
    error = hu.APIUserInputError(title="Schedule Too Frequent", detail=error_detail)
    cron_instance = Cron(cron_schedule)
    [minutes, hours, days, months, weekdays] = cron_instance.to_list()
    if len(minutes) > 1:
        # Means this will sometimes run at twice or more in one hour, which is too frequent
        raise error
    if len(hours) > 1:
        # Means this will sometimes run at twice or more in one day, which is too frequent
        raise error
    start_date = datetime.now()
    schedule = cron_instance.schedule(start_date)
    prev_date = schedule.next()
    # At this point we know that the schedule is not more frequence than once per day
    # This just creates schedules for next year (or more) and checks if any two consecutive
    # schedules have enough of a gap between them
    for i in range(365):
        date = schedule.next()
        if date - prev_date < timedelta(days=min_allowed_days_between_runs):
            raise error
        if date - start_date > timedelta(days=365):
            # Haven't found too frequent scheduled times in a year from now, that's enough
            return
        prev_date = date


def on_check_create(userinfo: UserInfo, check: hu.InCheckAttributes) -> None:
    print("ON CHECK CREATE")

    if userinfo["username"] not in ["alice", "bob"]:
        raise hu.APIForbiddenError(
            title="Check creation disallowed",
            detail="You are not authorized to create this check",
        )

    min_allowed_days_between_runs = 3
    if check.metadata.template_id == "telemetry_access_template":
        raise_error_if_schedule_too_frequent(
            check.schedule,
            min_allowed_days_between_runs=3,
            error_detail=f"Check from template {check.metadata.template_id} must run at most once in {min_allowed_days_between_runs} day period.",
        )


def on_check_remove(userinfo: UserInfo, check: hu.OutCheck) -> None:
    print("ON CHECK REMOVE")

    if userinfo["username"] not in ["alice", "bob"]:
        raise hu.APIForbiddenError(
            title="Unauthorized check remove",
            detail=f"You are not authorized to remove check with id {check.id}",
        )


def on_check_access(userinfo: UserInfo, check: hu.OutCheck) -> None:
    print("ON CHECK ACCESS")

    # raise CheckIdError(check_id)

    # raise hu.APIForbidden(
    #     title="Check created but access denied",
    #     detail="The check was created, but access to the resulting check was denied",
    # )


def on_check_run(userinfo: UserInfo, check: hu.OutCheck) -> None:
    print("ON CHECK RUN")

    # raise hu.APIForbidden(
    #     title="Unauthorized run check",
    #     detail=f"You are not authorized to run check with id {check.id}",
    # )


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
    userinfo: UserInfo,
    check_id: hu.CheckId,
    client: hu.K8sClient,
    cronjob: hu.K8sCronJob,
) -> None:
    print("on_k8s_cronjob_access")

    if cronjob.metadata.annotations.get("owner") != userinfo["username"]:
        raise hu.CheckIdError(check_id)


async def on_k8s_cronjob_create(
    userinfo: UserInfo, client: hu.K8sClient, cronjob: hu.K8sCronJob
) -> None:
    print("on_k8s_cronjob_create")

    ## Ensure cronjob is tagged with correct owner

    if (
        "owner" in cronjob.metadata.annotations
        and cronjob.metadata.annotations["owner"] != userinfo["username"]
    ):
        raise hu.APIForbiddenError(
            title="Unauthorized check create",
            detail="Permission denied to create health check cronjob",
        )

    cronjob.metadata.annotations["owner"] = userinfo["username"]

    ## Ensure the user has an offline token set
    ## Note: Would be more robust to check on every access but use a cache
    secret_name = f"resource-health-{userinfo['username']}-offline-secret"
    secret_namespace = get_k8s_namespace(userinfo)

    offline_secret = await hu.lookup_k8s_secret(
        client=client, namespace=secret_namespace, name=secret_name
    )

    if offline_secret is None:
        if userinfo["refresh_token"] is None:
            raise hu.APIException(
                status="404",
                code="MissingOfflineToken",
                title="Missing Offline Token",
                detail="Missing offline token, please create at least one check using the website",
            )
        await hu.create_k8s_secret(
            client=client,
            name=secret_name,
            namespace=secret_namespace,
            string_data={"offline_token": userinfo["refresh_token"]},
        )


def on_k8s_cronjob_remove(
    userinfo: UserInfo, client: hu.K8sClient, cronjob: hu.K8sCronJob
) -> None:
    print("on_k8s_cronjob_remove")

    ## Access already checked as part of on_k8s_cronjob_access

    # raise hu.APIForbidden(
    #     title="Unauthorized check remove",
    #     detail="Permission denied to remove health check cronjob",
    # )


def on_k8s_cronjob_run(
    userinfo: UserInfo, client: hu.K8sClient, cronjob: hu.K8sCronJob
) -> None:
    print("on_k8s_cronjob_run")

    ## Access already checked as part of on_k8s_cronjob_access

    # raise hu.APIForbidden(
    #     title="Unauthorized run check",
    #     detail="Permission denied to run health check cronjob",
    # )


## For the mock backend


def get_mock_username(userinfo: UserInfo) -> str:
    return userinfo["username"]
