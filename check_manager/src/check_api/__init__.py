import json
from typing import Annotated, Any
import pathlib
import os
from fastapi import (
    FastAPI,
    Path,
    Query,
    Request,
    Response,
    status,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from os import environ
from check_hooks import (
    call_hooks_check_if_allow,
    call_hooks_ignore_results,
    call_hooks_until_not_none,
    load_hooks,
)

from api_interface import (
    GET_CHECK_PATH,
    GET_CHECK_TEMPLATE_PATH,
    GET_CHECK_TEMPLATES_PATH,
    GET_CHECKS_PATH,
    CREATE_CHECK_PATH,
    REMOVE_CHECK_PATH,
    RUN_CHECK_PATH,
)
from api_utils.api_utils import (
    JSONAPIResponse,
    add_exception_handlers,
    get_api_router_with_defaults,
    get_env_var_or_throw,
    get_request_url_str,
    get_url_str,
    set_custom_json_schema,
)
from check_backends.check_backend import (
    CheckBackend,
    CheckIdError,
    CheckIdNonUniqueError,
    CheckTemplate,
    CheckTemplateId,
    CheckTemplateAttributes,
    CheckId,
    OutCheck,
    OutCheckAttributes,
    InCheck,
    CheckTemplateIdError,
)
from check_backends.mock_backend import MockBackend

# from check_backends.rest_backend import RestBackend
from check_backends.rest_backend import RestBackend
from exceptions import (
    APIException,
    NewCheckClientSpecifiedId,
)
from api_utils.json_api_types import (
    APIOKResponse,
    APIOKResponseList,
    Link,
    LinkObject,
    Links,
    Resource,
)

BASE_URL = get_env_var_or_throw("RH_CHECK_API_BASE_URL")

app = FastAPI()
# A solution to make CORS headers appear in error responses too, based on
# https://github.com/fastapi/fastapi/discussions/8027#discussioncomment-5146484
wrapped_app = CORSMiddleware(
    app=app,
    allow_origin_regex=".*",
    # Even though the below allows all things too, it disables returns Access-Control-Allow-Origin=* in the header
    # and borwsers don't allow to use that with withCredentials=True
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_exception_handlers(app)

loaded_hooks = load_hooks()


# Use CheckBackend type so mypy warns is any specifics of MockBackend are used
check_backend: CheckBackend = MockBackend(
    template_id_prefix="remote_", hooks=loaded_hooks
)

GET_FASTAPI_SECURITY_HOOK_NAME = (
    os.environ.get("GET_FASTAPI_SECURITY_HOOK_NAME") or "get_fastapi_security"
)
ON_AUTH_HOOK_NAME = os.environ.get("RH_CHECK_ON_AUTH_HOOK_NAME") or "on_auth"
ON_TEMPLATE_ACCESS_HOOK_NAME = (
    os.environ.get("RH_CHECK_ON_TEMPLATE_ACCESS_HOOK_NAME") or "on_template_access"
)
ON_CHECK_ACCESS_HOOK_NAME = (
    os.environ.get("RH_CHECK_ON_CHECK_ACCESS_HOOK_NAME") or "on_check_access"
)
ON_CHECK_CREATE_HOOK_NAME = (
    os.environ.get("RH_CHECK_ON_CHECK_CREATE_HOOK_NAME") or "on_check_create"
)
ON_CHECK_REMOVE_HOOK_NAME = (
    os.environ.get("RH_CHECK_ON_CHECK_REMOVE_HOOK_NAME") or "on_check_remove"
)
ON_CHECK_RUN_HOOK_NAME = (
    os.environ.get("RH_CHECK_ON_CHECK_RUN_HOOK_NAME") or "on_check_run"
)

## TODO: Make this configurable/optional


async def security_scheme(request: Request) -> Any | None:
    if GET_FASTAPI_SECURITY_HOOK_NAME in loaded_hooks:
        return await call_hooks_until_not_none(
            loaded_hooks[GET_FASTAPI_SECURITY_HOOK_NAME], request
        )
    else:
        return None


router = get_api_router_with_defaults()


# app. instead of router. because don't want to indicate that could return HTTP error 422
@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
    response_class=JSONAPIResponse,
)
async def root(
    auth_info: Annotated[Any, Depends(security_scheme)],
) -> APIOKResponseList[None, None]:
    if ON_AUTH_HOOK_NAME in loaded_hooks:
        auth_info = await call_hooks_until_not_none(
            loaded_hooks[ON_AUTH_HOOK_NAME], auth_info
        )

    ## NOTE: Maybe add on_root hook?

    return APIOKResponseList[None, None](
        data=[
            Resource[None](
                id="documentation_website",
                type="api_path",
                attributes=None,
                links={"self": get_url_str(BASE_URL, "/docs")},
            ),
            Resource[None](
                id="get_check_templates",
                type="api_path",
                attributes=None,
                links={"self": get_url_str(BASE_URL, GET_CHECK_TEMPLATES_PATH)},
            ),
            Resource[None](
                id="get_checks",
                type="api_path",
                attributes=None,
                links={"self": get_url_str(BASE_URL, GET_CHECKS_PATH)},
            ),
        ],
        links=Links(
            self=BASE_URL,
            describedby=LinkObject(
                title="OpenAPI schema", href=get_url_str(BASE_URL, "/openapi.json")
            ),
        ),
        meta=None,
    )


def check_template_url(check_template_id: CheckTemplateId) -> str:
    return get_url_str(
        BASE_URL,
        GET_CHECK_TEMPLATE_PATH,
        path_params={"check_template_id": check_template_id},
    )


def check_template_to_resource(
    template: CheckTemplate,
) -> Resource[CheckTemplateAttributes]:
    return Resource[CheckTemplateAttributes](
        id=template.id,
        type="check_template",
        attributes=template.attributes,
        links={"self": check_template_url(template.id)},
    )


@router.get(
    GET_CHECK_TEMPLATES_PATH,
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
)
async def get_check_templates(
    auth_info: Annotated[Any, Depends(security_scheme)],
    request: Request,
    response: Response,
    ids: Annotated[
        list[CheckTemplateId] | None,
        Query(description="restrict IDs to include"),
    ] = None,
) -> APIOKResponseList[CheckTemplateAttributes, None]:
    if ON_AUTH_HOOK_NAME in loaded_hooks:
        auth_info = await call_hooks_until_not_none(
            loaded_hooks[ON_AUTH_HOOK_NAME], auth_info
        )

    response.headers["Allow"] = "GET"
    return APIOKResponseList[CheckTemplateAttributes, None](
        data=[
            check_template_to_resource(template)
            async for template in check_backend.get_check_templates(auth_info, ids)
            if (
                ON_TEMPLATE_ACCESS_HOOK_NAME not in loaded_hooks
                or await call_hooks_check_if_allow(
                    loaded_hooks[ON_TEMPLATE_ACCESS_HOOK_NAME], auth_info, template
                )
            )
        ],
        links=Links(
            self=get_request_url_str(BASE_URL, request),
            root=BASE_URL,
        ),
        meta=None,
    )


async def _get_specific_check_template(
    auth_info: Any, check_template_id: CheckTemplateId
) -> CheckTemplate:
    check_templates = []

    async for check_template in check_backend.get_check_templates(
        auth_info, ids=[check_template_id]
    ):
        if ON_TEMPLATE_ACCESS_HOOK_NAME in loaded_hooks:
            await call_hooks_ignore_results(
                loaded_hooks[ON_TEMPLATE_ACCESS_HOOK_NAME], auth_info, check_template
            )
        check_templates.append(check_template)

    match check_templates:
        case []:
            raise CheckTemplateIdError(check_template_id)
        case [check_template]:
            return check_template
        case _:
            raise APIException(
                status="400",
                code="CheckTemplateIdNotUnique",
                title="Check template id is not unique",
                detail=f"Check template id {check_template_id} is not unique",
            )


@router.get(
    GET_CHECK_TEMPLATE_PATH,
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
)
async def get_check_template(
    auth_info: Annotated[Any, Depends(security_scheme)],
    request: Request,
    response: Response,
    check_template_id: CheckTemplateId,
) -> APIOKResponse[CheckTemplateAttributes]:
    if ON_AUTH_HOOK_NAME in loaded_hooks:
        auth_info = await call_hooks_until_not_none(
            loaded_hooks[ON_AUTH_HOOK_NAME], auth_info
        )

    check_template = await _get_specific_check_template(auth_info, check_template_id)

    response.headers["Allow"] = "GET"
    return APIOKResponse[CheckTemplateAttributes](
        data=check_template_to_resource(check_template),
        links=Links(
            self=get_request_url_str(BASE_URL, request),
            root=BASE_URL,
        ),
    )


def check_url(check_id: CheckId) -> str:
    return get_url_str(BASE_URL, GET_CHECK_PATH, path_params={"check_id": check_id})


def check_to_resource(check: OutCheck) -> Resource[OutCheckAttributes]:
    links: dict[str, Link] = {"self": check_url(check.id)}
    if check.attributes.metadata.template_id is not None:
        links["check_template"] = check_template_url(
            check.attributes.metadata.template_id
        )
    return Resource[OutCheckAttributes](
        id=check.id,
        type="check",
        attributes=check.attributes,
        links=links,
    )


@router.get(
    GET_CHECKS_PATH,
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
)
async def get_checks(
    auth_info: Annotated[Any, Depends(security_scheme)],
    request: Request,
    response: Response,
    ids: Annotated[
        list[CheckId] | None,
        Query(description="restrict IDs to include"),
    ] = None,
) -> APIOKResponseList[OutCheckAttributes, None]:
    if ON_AUTH_HOOK_NAME in loaded_hooks:
        auth_info = await call_hooks_until_not_none(
            loaded_hooks[ON_AUTH_HOOK_NAME], auth_info
        )

    response.headers["Allow"] = "GET,POST"
    return APIOKResponseList[OutCheckAttributes, None](
        data=[
            check_to_resource(check)
            async for check in check_backend.get_checks(auth_info, ids)
            if (
                ON_CHECK_ACCESS_HOOK_NAME not in loaded_hooks
                or await call_hooks_check_if_allow(
                    loaded_hooks[ON_CHECK_ACCESS_HOOK_NAME], auth_info, check
                )
            )
        ],
        links=Links(self=get_request_url_str(BASE_URL, request), root=BASE_URL),
        meta=None,
    )


@router.post(
    CREATE_CHECK_PATH,
    status_code=status.HTTP_201_CREATED,
    response_model_exclude_unset=True,
)
async def create_check(
    auth_info: Annotated[Any, Depends(security_scheme)],
    request: Request,
    response: Response,
    in_check: InCheck,
) -> APIOKResponse[OutCheckAttributes]:
    if ON_AUTH_HOOK_NAME in loaded_hooks:
        auth_info = await call_hooks_until_not_none(
            loaded_hooks[ON_AUTH_HOOK_NAME], auth_info
        )

    if hasattr(in_check.data, "id"):
        raise NewCheckClientSpecifiedId()
    assert in_check.data.type == "check"

    if ON_TEMPLATE_ACCESS_HOOK_NAME in loaded_hooks:
        check_template = await _get_specific_check_template(
            auth_info, in_check.data.attributes.metadata.template_id
        )

        await call_hooks_ignore_results(
            loaded_hooks[ON_TEMPLATE_ACCESS_HOOK_NAME], auth_info, check_template
        )

    if ON_CHECK_CREATE_HOOK_NAME in loaded_hooks:
        await call_hooks_ignore_results(
            loaded_hooks[ON_CHECK_CREATE_HOOK_NAME], auth_info, in_check.data.attributes
        )

    check = await check_backend.create_check(auth_info, in_check.data.attributes)

    if ON_CHECK_ACCESS_HOOK_NAME in loaded_hooks:
        await call_hooks_ignore_results(
            loaded_hooks[ON_CHECK_ACCESS_HOOK_NAME], auth_info, check
        )

    response.headers["Allow"] = "GET,POST"
    response.headers["Location"] = check_url(check.id)
    return APIOKResponse[OutCheckAttributes](
        data=check_to_resource(check),
        links=Links(root=BASE_URL),
    )


async def get_check_from_backend(auth_info: Any, check_id: CheckId) -> OutCheck:
    checks = [
        check async for check in check_backend.get_checks(auth_info, ids=[check_id])
    ]
    match checks:
        case []:
            raise CheckIdError(check_id)
        case [check]:
            if ON_CHECK_ACCESS_HOOK_NAME in loaded_hooks:
                await call_hooks_ignore_results(
                    loaded_hooks[ON_CHECK_ACCESS_HOOK_NAME], auth_info, check
                )
            return check
        case _:
            raise CheckIdNonUniqueError(f"Check id {check_id} is not unique")


@router.get(
    GET_CHECK_PATH,
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
)
async def get_check(
    auth_info: Annotated[Any, Depends(security_scheme)],
    request: Request,
    response: Response,
    check_id: CheckId,
) -> APIOKResponse[OutCheckAttributes]:
    if ON_AUTH_HOOK_NAME in loaded_hooks:
        auth_info = await call_hooks_until_not_none(
            loaded_hooks[ON_AUTH_HOOK_NAME], auth_info
        )

    check = await get_check_from_backend(auth_info, check_id)

    response.headers["Allow"] = "GET,DELETE"
    return APIOKResponse[OutCheckAttributes](
        data=check_to_resource(check),
        links=Links(
            self=get_request_url_str(BASE_URL, request),
            root=BASE_URL,
        ),
    )


# @router.patch(UPDATE_CHECK_PATH, status_code=status.HTTP_200_OK,
#    response_model_exclude_unset=True)
# async def update_check(
#     check_id: Annotated[CheckId, Path()],
#     template_id: Annotated[CheckTemplateId | None, Body()] = None,
#     template_args: Annotated[Json | None, Body()] = None,
#     schedule: Annotated[CronExpression | None, Body()] = None,
# ) -> Check:
#     return await check_backend.update_check(
#         tokens, check_id, template_id, template_args, schedule
#     )


@router.delete(
    REMOVE_CHECK_PATH,
    status_code=status.HTTP_204_NO_CONTENT,
    response_model_exclude_unset=True,
)
async def remove_check(
    auth_info: Annotated[Any, Depends(security_scheme)],
    response: Response,
    check_id: Annotated[CheckId, Path()],
) -> None:
    if ON_AUTH_HOOK_NAME in loaded_hooks:
        auth_info = await call_hooks_until_not_none(
            loaded_hooks[ON_AUTH_HOOK_NAME], auth_info
        )

    check = await get_check_from_backend(auth_info, check_id)

    if ON_CHECK_REMOVE_HOOK_NAME in loaded_hooks:
        await call_hooks_ignore_results(
            loaded_hooks[ON_CHECK_REMOVE_HOOK_NAME], auth_info, check
        )

    response.headers["Allow"] = "GET,DELETE"
    return await check_backend.remove_check(auth_info, check_id)


@router.post(
    RUN_CHECK_PATH,
    status_code=status.HTTP_204_NO_CONTENT,
    response_model_exclude_unset=True,
)
async def run_check(
    auth_info: Annotated[Any, Depends(security_scheme)],
    response: Response,
    check_id: Annotated[CheckId, Path()],
) -> None:
    if ON_AUTH_HOOK_NAME in loaded_hooks:
        auth_info = await call_hooks_until_not_none(
            loaded_hooks[ON_AUTH_HOOK_NAME], auth_info
        )

    check = await get_check_from_backend(auth_info, check_id)

    if ON_CHECK_RUN_HOOK_NAME in loaded_hooks:
        await call_hooks_ignore_results(
            loaded_hooks[ON_CHECK_RUN_HOOK_NAME], auth_info, check
        )

    response.headers["Allow"] = "POST"
    return await check_backend.run_check(auth_info, check_id)


app.include_router(router)

set_custom_json_schema(app, "Check Manager API", "v1")


def uvicorn_dev() -> None:
    with open("openapi.json", mode="w+") as file:
        json.dump(app.openapi(), file, indent=2)

    # NOTE: this will not work in case reload=True in uvicorn.run function.
    # The workaround for now is to comment out reload=True

    global check_backend
    if environ.get("BACKEND") == "REST":
        check_backend = RestBackend("http://127.0.0.1:8000/")

    import uvicorn

    port = environ.get("PORT")
    uvicorn.run(
        "check_api:wrapped_app",
        port=int(port) if port else 8000,
        # reload=True,
        root_path=environ.get("FAST_API_ROOT_PATH") or "",
    )


def unicorn_dummy_prod() -> None:
    import uvicorn

    uvicorn.run(
        "check_api:wrapped_app",
        host="0.0.0.0",
        reload=True,
        root_path=environ.get("FAST_API_ROOT_PATH") or "",
    )


def uvicorn_k8s() -> None:
    from check_backends.k8s_backend import K8sBackend

    import check_backends.k8s_backend.default_templates as default_templates

    templates_path: str = os.environ.get("RH_CHECK_K8S_TEMPLATE_PATH") or str(
        pathlib.Path(default_templates.__file__).resolve().parent
    )

    global check_backend

    check_backend = K8sBackend[Any](
        template_dirs=[templates_path],
        hooks=loaded_hooks,
        # load_authentication(Settings().auth_hooks),
        # load_authentication(pathlib.Path("hooks/hooks.py")),
    )

    import uvicorn

    # This is the host fastapi run uses, see https://fastapi.tiangolo.com/it/fastapi-cli/#fastapi-run
    uvicorn.run(
        wrapped_app, host="0.0.0.0", root_path=environ.get("FAST_API_ROOT_PATH") or ""
    )


if __name__ == "__main__":
    uvicorn_dev()
