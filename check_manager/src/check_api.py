import json
from logging import warning
from typing import Annotated, Any
from fastapi import (
    APIRouter,
    FastAPI,
    Path,
    Query,
    Request,
    Response,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from os import environ

from api_interface import (
    GET_CHECK_PATH,
    GET_CHECK_TEMPLATE_PATH,
    Json,
    ERROR_CODE_KEY,
    ERROR_MESSAGE_KEY,
    LIST_CHECK_TEMPLATES_PATH,
    LIST_CHECKS_PATH,
    NEW_CHECK_PATH,
    REMOVE_CHECK_PATH,
)
from check_backends import (
    AuthenticationObject,
    CheckBackend,
    CronExpression,
    CheckTemplateId,
    CheckId,
    Check,
    MockBackend,
)
from check_backends.check_backend import CheckTemplate
from exceptions import (
    CheckException,
    CheckIdNonUniqueError,
    CheckInternalError,
    CheckTemplateIdError,
    CheckIdError,
    NewCheckClientSpecifiedId,
)


def get_my_url() -> str:
    my_url = environ.get("MY_URL")
    if my_url is None:
        raise ValueError("Environment variable MY_URL must be set")
    return my_url


MY_URL = get_my_url()


class CheckDefinition(BaseModel):
    check_template_id: CheckTemplateId
    check_template_args: Json
    schedule: CronExpression


# Dummy for now
auth_obj = AuthenticationObject("user1")
# Use type CheckBackend to ensure that the current backend could be replaced by any other without breaking anything
check_backend: CheckBackend = MockBackend(template_id_prefix="remote_")

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LinkObject(BaseModel):
    href: str
    # rel: str | None = None
    # describedby: str | None = None
    title: str | None = None
    # Double comment so that mypy doesn't think I'm trying to specify type using comment
    ## type: str | None = None
    # hreflang: str | None = None
    # meta: Json | None = None


type Link = str | LinkObject


# class Relationships(BaseModel):
#     links: dict[str, Link] | None = None
#     data: object | None = None
#     meta: object | None = None


class Links(BaseModel):
    self: Link | None = None
    # related: object | None = None
    describedby: Link | None = None
    # first: Link | None = None
    # last: Link | None = None
    # prev: Link | None = None
    # next: Link | None = None


class Resource(BaseModel):
    id: str
    type: str
    attributes: object | None = None
    # relationships: object | None = None
    links: dict[str, Link] | None = None
    # meta: object | None = None


# class ResourceIdentifier(BaseModel):
#     id: str
# Double comment so that mypy doesn't think I'm trying to specify type using comment
##     type: str
#     meta: object | None = None


class Error(BaseModel):
    # id: str | None = None
    # links: dict[str, Link] | None = None
    # status: str | None = None
    code: str | None = None
    title: str | None = None
    detail: str | None = None
    # source: str | None = None
    meta: object | None = None


class APIOKResponse(BaseModel):
    data: (
        Resource | list[Resource] | None
        # | ResourceIdentifier | list[ResourceIdentifier]
    )
    # meta: Json | None = None
    # jsonapi: Json | None = None
    links: Links | None = None
    # included: list[Resource] | None = None


class APIErrorResponse(BaseModel):
    errors: list[Error] | None = None
    # meta: Json | None = None
    # jsonapi: Json | None = None
    # links: Links | None = None


class JSONAPIResponse(JSONResponse):
    media_type = "application/vnd.api+json"


router = APIRouter(
    default_response_class=JSONAPIResponse,
    responses={status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": APIErrorResponse}},
)


def get_status_code_and_error(exception: BaseException) -> tuple[int, Error]:
    if not isinstance(exception, CheckException):
        exception = CheckInternalError("Internal server error")
    error: Error = Error(code=type(exception).__name__, detail=str(exception))
    match exception:
        case NewCheckClientSpecifiedId():
            return (403, error)
        case CheckIdError() | CheckTemplateIdError():
            return (404, error)
        case _:
            return (500, error)


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception) -> JSONAPIResponse:
    (status_code, error) = get_status_code_and_error(exc)
    return JSONAPIResponse(
        status_code=status_code,
        content=jsonable_encoder(APIErrorResponse(errors=[error]), exclude_unset=True),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONAPIResponse:
    def mangle_error(error: dict[str, Any]) -> Error:
        type: str = error.pop("type")
        msg: str = error.pop("msg")
        loc: tuple = error.pop("loc")
        if loc[0] == "body":
            loc = loc[1:]
        _input = error.pop("input")
        # TODO: turn loc into a valid JSON Pointer
        # The difficulty is that sometimes the last element is int, and when the field is missing it points to the missing field
        # though json pointers must be valid. There might be some other edge cases with which I don't want to deal with for now
        return Error(
            code=type,
            title=msg,
            meta={**error, "loc": "/" + "/".join([str(name) for name in loc])},
        )

    warning(f"{exc.errors()}")
    return JSONAPIResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            APIErrorResponse(errors=[mangle_error(error) for error in exc.errors()]),
            exclude_unset=True,
        ),
    )


# app. instead of router. because don't want to indicate that could return HTTP error 422
@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
    response_class=JSONAPIResponse,
)
async def root() -> APIOKResponse:
    return APIOKResponse(
        data=[
            Resource(
                id="documentation_website",
                type="api_path",
                links={"self": MY_URL + "/docs"},
            ),
            Resource(
                id="list_check_templates",
                type="api_path",
                links={"self": MY_URL + LIST_CHECK_TEMPLATES_PATH},
            ),
            Resource(
                id="list_checks",
                type="api_path",
                links={"self": MY_URL + LIST_CHECKS_PATH},
            ),
        ],
        links=Links(
            self=MY_URL,
            describedby=LinkObject(
                title="OpenAPI schema", href=MY_URL + "/openapi.json"
            ),
        ),
    )


def check_template_url(check_template_id: CheckTemplateId) -> str:
    return MY_URL + GET_CHECK_TEMPLATE_PATH.format(check_template_id=check_template_id)


def check_template_to_resource(check_template: CheckTemplate) -> Resource:
    return Resource(
        id=check_template.id,
        type="check_template",
        attributes={
            "metadata": check_template.metadata,
            "arguments": check_template.arguments,
        },
        links={"self": check_template_url(check_template.id)},
    )


@router.get(
    GET_CHECK_TEMPLATE_PATH,
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
)
async def get_check_template(
    check_template_id: CheckTemplateId, response: Response
) -> APIOKResponse:
    check_templates = [
        check_template
        async for check_template in check_backend.list_check_templates(
            ids=[check_template_id]
        )
    ]
    match check_templates:
        case []:
            raise CheckIdError(
                f"Check template with id {check_template_id} doesn't exist"
            )
        case [check_template]:
            response.headers["Allow"] = "GET"
            return APIOKResponse(data=check_template_to_resource(check_template))
        case _:
            raise CheckException(f"Check template id {check_template_id} is not unique")


@router.get(
    LIST_CHECK_TEMPLATES_PATH,
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
)
## filter: conditions to filter on Metadata
async def list_check_templates(
    response: Response,
    ids: Annotated[
        list[CheckTemplateId] | None, Query(description="restrict IDs to include")
    ] = None,
) -> APIOKResponse:
    response.headers["Allow"] = "GET"
    return APIOKResponse(
        data=[
            check_template_to_resource(check_template)
            async for check_template in check_backend.list_check_templates(ids)
        ],
        links=Links(self=MY_URL + LIST_CHECK_TEMPLATES_PATH),
    )


class NewCheckAttributes(BaseModel):
    template_id: CheckTemplateId
    template_args: Json
    schedule: CronExpression


class NewCheckData(BaseModel):
    type: str = "check"
    attributes: NewCheckAttributes


class NewCheck(BaseModel):
    data: NewCheckData


def check_url(check_id: CheckId) -> str:
    return MY_URL + GET_CHECK_PATH.format(check_id=check_id)


def check_to_resource(check: Check) -> Resource:
    links: dict[str, Link] = {"self": check_url(check.id)}
    if "template" in check.metadata:
        links["check_template"] = check_template_url(check.metadata["template"])
    return Resource(
        id=check.id,
        type="check",
        attributes={
            "metadata": check.metadata,
            "schedule": check.schedule,
            "outcome_filter": check.outcome_filter,
        },
        links=links,
    )


# def application_vnd(content_type: str = Header(...)):
#     """Require request MIME-type to be application/vnd.api+json"""

#     if content_type != "application/vnd.api+json":
#         raise HTTPException(
#             status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
#             f"Unsupported media type: {content_type}."
#             " It must be application/vnd.api+json",
#         )


@router.post(
    NEW_CHECK_PATH,
    status_code=status.HTTP_201_CREATED,
    response_model_exclude_unset=True,
    # dependencies=[Depends(application_vnd)],
)
async def new_check(
    new_check: NewCheck,
    response: Response,
) -> APIOKResponse:
    if hasattr(new_check.data, "id"):
        raise NewCheckClientSpecifiedId()
    assert new_check.data.type == "check"
    check = await check_backend.new_check(
        auth_obj,
        new_check.data.attributes.template_id,
        new_check.data.attributes.template_args,
        new_check.data.attributes.schedule,
    )
    response.headers["Allow"] = "GET,POST"
    response.headers["Location"] = check_url(check.id)
    return APIOKResponse(data=check_to_resource(check))


@router.get(
    GET_CHECK_PATH,
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
)
async def get_check(check_id: CheckId, response: Response) -> APIOKResponse:
    checks = [
        check async for check in check_backend.list_checks(auth_obj, ids=[check_id])
    ]
    match checks:
        case []:
            raise CheckIdError(f"Check with id {check_id} doesn't exist")
        case [check]:
            response.headers["Allow"] = "GET,DELETE"
            return APIOKResponse(data=check_to_resource(check))
        case _:
            raise CheckIdNonUniqueError(f"Check id {check_id} is not unique")


# @router.patch(UPDATE_CHECK_PATH, status_code=status.HTTP_200_OK,
#    response_model_exclude_unset=True)
# async def update_check(
#     check_id: Annotated[CheckId, Path()],
#     template_id: Annotated[CheckTemplateId | None, Body()] = None,
#     template_args: Annotated[Json | None, Body()] = None,
#     schedule: Annotated[CronExpression | None, Body()] = None,
# ) -> Check:
#     return await check_backend.update_check(
#         auth_obj, check_id, template_id, template_args, schedule
#     )


@router.delete(
    REMOVE_CHECK_PATH,
    status_code=status.HTTP_204_NO_CONTENT,
    response_model_exclude_unset=True,
)
async def remove_check(
    check_id: Annotated[CheckId, Path()], response: Response
) -> None:
    response.headers["Allow"] = "GET,DELETE"
    return await check_backend.remove_check(auth_obj, check_id)


@router.get(
    LIST_CHECKS_PATH,
    status_code=status.HTTP_200_OK,
    response_model_exclude_unset=True,
)
async def list_checks(
    response: Response,
    ids: Annotated[
        list[CheckId] | None, Query(description="restrict IDs to include")
    ] = None,
) -> APIOKResponse:
    response.headers["Allow"] = "GET,POST"
    return APIOKResponse(
        data=[
            check_to_resource(check)
            async for check in check_backend.list_checks(auth_obj, ids)
        ]
    )


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Custom title",
        version="2.5.0",
        summary="This is a very custom OpenAPI schema",
        description="Here's a longer description of the custom **OpenAPI** schema",
        routes=app.routes,
    )

    for _, path_schema in openapi_schema["paths"].items():
        for _, method_schema in path_schema.items():
            if "requestBody" in method_schema:
                content: dict[str, Any] = method_schema["requestBody"]["content"]
                content["application/vnd.api+json"] = content.pop("application/json")
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.include_router(router)

app.openapi = custom_openapi  # type: ignore


def uvicorn_dev() -> None:
    with open("openapi.json", mode="w+") as file:
        json.dump(app.openapi(), file, indent=2)

    import uvicorn

    uvicorn.run(
        "check_api:app", reload=True, root_path=environ.get("FAST_API_ROOT_PATH") or ""
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
    from check_backends import K8sBackend

    global check_backend
    check_backend = K8sBackend("Cluster")

    import uvicorn

    # This is the host fastapi run uses, see https://fastapi.tiangolo.com/it/fastapi-cli/#fastapi-run
    uvicorn.run(app, host="0.0.0.0", root_path=environ.get("FAST_API_ROOT_PATH") or "")


if __name__ == "__main__":
    uvicorn_dev()
