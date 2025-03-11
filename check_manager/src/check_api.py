import json
from typing import Annotated, Iterable, assert_never
from fastapi import Body, FastAPI, Path, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from os import environ

from api_interface import (
    Json,
    ERROR_CODE_KEY,
    ERROR_MESSAGE_KEY,
    LIST_CHECK_TEMPLATES_PATH,
    LIST_CHECKS_PATH,
    NEW_CHECK_PATH,
    REMOVE_CHECK_PATH,
    UPDATE_CHECK_PATH,
    get_exception,
)
from check_backends import (
    AuthenticationObject,
    CheckBackend,
    CronExpression,
    CheckTemplateId,
    CheckId,
    Json,
    CheckTemplate,
    Check,
    MockBackend,
)
from exceptions import (
    CheckException,
    CheckInternalError,
    CheckTemplateIdError,
    CheckIdError,
    CheckIdNonUniqueError,
)


def get_status_code_and_message(exception: BaseException) -> tuple[int, Json]:
    if not isinstance(exception, CheckException):
        exception = CheckInternalError("Internal server error")
    error_json: dict[str, object] = {
        ERROR_CODE_KEY: type(exception).__name__,
        ERROR_MESSAGE_KEY: str(exception),
    }
    match exception:
        case CheckIdError() | CheckTemplateIdError():
            return (404, error_json)
        case _:
            return (500, error_json)


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


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    (status_code, content) = get_status_code_and_message(exc)
    return JSONResponse(status_code=status_code, content=content)


@app.get(LIST_CHECK_TEMPLATES_PATH, status_code=status.HTTP_200_OK)
## filter: conditions to filter on Metadata
async def list_check_templates(
    ids: Annotated[
        list[CheckTemplateId] | None, Query(description="restrict IDs to include")
    ] = None,
) -> Iterable[CheckTemplate]:
    # TODO: stream this instead of accumulating everything first
    return [
        check_template
        async for check_template in check_backend.list_check_templates(ids)
    ]


@app.post(NEW_CHECK_PATH, status_code=status.HTTP_201_CREATED)
async def new_check(
    template_id: Annotated[CheckTemplateId, Body()],
    template_args: Annotated[Json, Body()],
    schedule: Annotated[CronExpression, Body()],
) -> Check:
    return await check_backend.new_check(auth_obj, template_id, template_args, schedule)


# @app.patch(UPDATE_CHECK_PATH, status_code=status.HTTP_200_OK)
# async def update_check(
#     check_id: Annotated[CheckId, Path()],
#     template_id: Annotated[CheckTemplateId | None, Body()] = None,
#     template_args: Annotated[Json | None, Body()] = None,
#     schedule: Annotated[CronExpression | None, Body()] = None,
# ) -> Check:
#     return await check_backend.update_check(
#         auth_obj, check_id, template_id, template_args, schedule
#     )


@app.delete(REMOVE_CHECK_PATH, status_code=status.HTTP_204_NO_CONTENT)
async def remove_check(check_id: Annotated[CheckId, Path()]) -> None:
    return await check_backend.remove_check(auth_obj, check_id)


@app.get(LIST_CHECKS_PATH, status_code=status.HTTP_200_OK)
async def list_checks(
    ids: Annotated[
        list[CheckId] | None, Query(description="restrict IDs to include")
    ] = None,
) -> Iterable[Check]:
    # TODO: stream this instead of accumulating everything first
    return [check async for check in check_backend.list_checks(auth_obj, ids)]

@app.get("/healthz", include_in_schema=False)
async def healthz() -> str:
    return "OK"

@app.get("/livez", include_in_schema=False)
async def livez() -> str:
    return "OK"

@app.get("/readyz", include_in_schema=False)
async def readyz() -> str:
    return "OK"

def uvicorn_dev() -> None:
    with open("openapi.json", mode="w+") as file:
        json.dump(app.openapi(), file, indent=2)

    import uvicorn

    uvicorn.run("check_api:app", reload=True, root_path=environ.get("FAST_API_ROOT_PATH") or "")


def unicorn_dummy_prod() -> None:
    import uvicorn

    uvicorn.run("check_api:app", host="0.0.0.0", reload=True, root_path=environ.get("FAST_API_ROOT_PATH") or "")


def uvicorn_k8s() -> None:
    from check_backends import K8sBackend

    global check_backend
    check_backend = K8sBackend(["templates"])

    import uvicorn

    # This is the host fastapi run uses, see https://fastapi.tiangolo.com/it/fastapi-cli/#fastapi-run
    uvicorn.run(app, host="0.0.0.0", root_path=environ.get("FAST_API_ROOT_PATH") or "")


if __name__ == "__main__":
    uvicorn_dev()
