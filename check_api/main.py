import json
from typing import Annotated, Iterable
from fastapi import Body, FastAPI, Path, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from lib import (
    LIST_CHECK_TEMPLATES_PATH,
    LIST_CHECKS_PATH,
    NEW_CHECK_PATH,
    REMOVE_CHECK_PATH,
    UPDATE_CHECK_PATH,
    AuthenticationObject,
    CheckBackend,
    CronExpression,
    CheckTemplateId,
    CheckId,
    Json,
    CheckTemplate,
    Check,
    MockBackend,
    get_status_code_and_message,
)


class CheckDefinition(BaseModel):
    check_template_id: CheckTemplateId
    check_template_args: Json
    schedule: CronExpression


# Dummy for now
auth_obj = AuthenticationObject("user1")
# Use type CheckBackend to ensure that the current backend could be replaced by any other without breaking anything
check_backend: CheckBackend = MockBackend()

app = FastAPI()


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
    return await check_backend.list_check_templates(ids)


@app.post(NEW_CHECK_PATH, status_code=status.HTTP_201_CREATED)
async def new_check(
    template_id: Annotated[CheckTemplateId, Body()],
    template_args: Annotated[Json, Body()],
    schedule: Annotated[CronExpression, Body()],
) -> Check:
    return await check_backend.new_check(auth_obj, template_id, template_args, schedule)


@app.patch(UPDATE_CHECK_PATH, status_code=status.HTTP_200_OK)
async def update_check(
    check_id: Annotated[CheckId, Path()],
    template_id: Annotated[CheckTemplateId | None, Body()] = None,
    template_args: Annotated[Json, Body()] = None,
    schedule: Annotated[CronExpression | None, Body()] = None,
) -> Check:
    return await check_backend.update_check(
        auth_obj, check_id, template_id, template_args, schedule
    )


@app.delete(REMOVE_CHECK_PATH, status_code=status.HTTP_204_NO_CONTENT)
async def remove_check(check_id: Annotated[CheckId, Path()]) -> None:
    return await check_backend.remove_check(auth_obj, check_id)


@app.get(LIST_CHECKS_PATH, status_code=status.HTTP_200_OK)
async def list_checks(
    ids: Annotated[
        list[CheckId] | None, Query(description="restrict IDs to include")
    ] = None,
) -> Iterable[Check]:
    return await check_backend.list_checks(auth_obj, ids)


# This needs to be at the bottom so that all methods, error handlers, and such are already defined
with open("openapi.json", mode="w+") as file:
    json.dump(app.openapi(), file, indent=2)
