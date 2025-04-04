import json
from typing import Annotated
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
import pathlib

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
    AuthenticationObject,
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
    Error,
    Link,
    LinkObject,
    Links,
    Resource,
)

from eoepca_security import OIDCProxyScheme, Tokens

BASE_URL = get_env_var_or_throw("RH_CHECK_API_BASE_URL")


# Use CheckBackend type so mypy warns is any specifics of MockBackend are used
check_backend: CheckBackend = MockBackend(template_id_prefix="remote_")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    # Even though the below allows all things too, it disables returns Access-Control-Allow-Origin=* in the header
    # and borwsers don't allow to use that with withCredentials=True
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
add_exception_handlers(app)

## TODO: Make this configurable/optional
security_scheme = OIDCProxyScheme(
    openIdConnectUrl=get_env_var_or_throw('OPEN_ID_CONNECT_URL'),
    audience=get_env_var_or_throw('OPEN_ID_CONNECT_AUDIENCE'),
    id_token_header="x-id-token",
    refresh_token_header="x-refresh-token",
    auth_token_header="Authorization",
    auth_token_in_authorization=True,
    auto_error=True, ## Set False to allow unauthenticated access!
    scheme_name="OIDC behind auth proxy",
)

router = get_api_router_with_defaults()


# app. instead of router. because don't want to indicate that could return HTTP error 422
@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
    response_class=JSONAPIResponse,
)
async def root(tokens: Annotated[Tokens, Depends(security_scheme)]) -> APIOKResponseList[None, None]:
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
    tokens: Annotated[Tokens, Depends(security_scheme)],
    request: Request,
    response: Response,
    ids: Annotated[
        list[CheckTemplateId] | None,
        Query(description="restrict IDs to include"),
    ] = None,
) -> APIOKResponseList[CheckTemplateAttributes, None]:
    response.headers["Allow"] = "GET"
    return APIOKResponseList[CheckTemplateAttributes, None](
        data=[
            check_template_to_resource(template)
            async for template in check_backend.get_check_templates(tokens, ids)
        ],
        links=Links(
            self=get_request_url_str(BASE_URL, request),
            root=BASE_URL,
        ),
        meta=None,
    )


@router.get(
    GET_CHECK_TEMPLATE_PATH,
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
)
async def get_check_template(
    tokens: Annotated[Tokens, Depends(security_scheme)],
    request: Request,
    response: Response,
    check_template_id: CheckTemplateId
) -> APIOKResponse[CheckTemplateAttributes]:
    check_templates = [
        check_template
        async for check_template in check_backend.get_check_templates(
            ids=[check_template_id]
        )
    ]
    match check_templates:
        case []:
            raise CheckTemplateIdError.create(check_template_id)
        case [check_template]:
            response.headers["Allow"] = "GET"
            return APIOKResponse[CheckTemplateAttributes](
                data=check_template_to_resource(check_template),
                links=Links(
                    self=get_request_url_str(BASE_URL, request),
                    root=BASE_URL,
                ),
            )
        case _:
            raise APIException(
                Error(
                    status="400",
                    code="CheckTemplateIdNotUnique",
                    title="Check template id is not unique",
                    detail=f"Check template id {check_template_id} is not unique",
                )
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
    tokens: Annotated[Tokens, Depends(security_scheme)],
    request: Request,
    response: Response,
    ids: Annotated[
        list[CheckId] | None,
        Query(description="restrict IDs to include"),
    ] = None,
) -> APIOKResponseList[OutCheckAttributes, None]:
    response.headers["Allow"] = "GET,POST"
    return APIOKResponseList[OutCheckAttributes, None](
        data=[
            check_to_resource(check)
            async for check in check_backend.get_checks(tokens, ids)
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
    tokens: Annotated[Tokens, Depends(security_scheme)],
    request: Request,
    response: Response,
    in_check: InCheck,
) -> APIOKResponse[OutCheckAttributes]:
    if hasattr(in_check.data, "id"):
        raise NewCheckClientSpecifiedId.create()
    assert in_check.data.type == "check"
    check = await check_backend.create_check(tokens, in_check.data.attributes)
    response.headers["Allow"] = "GET,POST"
    response.headers["Location"] = check_url(check.id)
    return APIOKResponse[OutCheckAttributes](
        data=check_to_resource(check),
        links=Links(root=BASE_URL),
    )


@router.get(
    GET_CHECK_PATH,
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
)
async def get_check(
    tokens: Annotated[Tokens, Depends(security_scheme)],
    request: Request,
    response: Response,
    check_id: CheckId
) -> APIOKResponse[OutCheckAttributes]:
    checks = [
        check async for check in check_backend.get_checks(tokens, ids=[check_id])
    ]
    match checks:
        case []:
            raise CheckIdError.create(check_id)
        case [check]:
            response.headers["Allow"] = "GET,DELETE"
            return APIOKResponse[OutCheckAttributes](
                data=check_to_resource(check),
                links=Links(
                    self=get_request_url_str(BASE_URL, request),
                    root=BASE_URL,
                ),
            )
        case _:
            raise CheckIdNonUniqueError.create(check_id)


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
    tokens: Annotated[Tokens, Depends(security_scheme)],
    response: Response,
    check_id: Annotated[CheckId, Path()]
) -> None:
    response.headers["Allow"] = "GET,DELETE"
    return await check_backend.remove_check(tokens, check_id)


@router.post(
    RUN_CHECK_PATH,
    status_code=status.HTTP_204_NO_CONTENT,
    response_model_exclude_unset=True,
)
async def run_check(
    tokens: Annotated[Tokens, Depends(security_scheme)],
    response: Response,
    check_id: Annotated[CheckId, Path()]
) -> None:
    response.headers["Allow"] = "POST"
    return await check_backend.run_check(tokens, check_id)


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
        "check_api:app",
        port=int(port) if port else 8000,
        # reload=True,
        root_path=environ.get("FAST_API_ROOT_PATH") or "",
    )


def unicorn_dummy_prod() -> None:
    import uvicorn

    uvicorn.run(
        "check_api:app",
        host="0.0.0.0",
        reload=True,
        root_path=environ.get("FAST_API_ROOT_PATH") or "",
    )


def uvicorn_k8s() -> None:
    from check_backends.k8s_backend import K8sBackend
    from security import Settings, load_authentication

    global check_backend
    check_backend = K8sBackend[AuthenticationObject](
        ["templates", "src/check_backends/k8s_backend/template_examples"],
        # load_authentication(Settings().auth_hooks),
        load_authentication(pathlib.Path("hooks/hooks.py")),
    )

    import uvicorn

    # This is the host fastapi run uses, see https://fastapi.tiangolo.com/it/fastapi-cli/#fastapi-run
    uvicorn.run(app, host="0.0.0.0", root_path=environ.get("FAST_API_ROOT_PATH") or "")


if __name__ == "__main__":
    uvicorn_dev()
