import json
from typing import Annotated, Iterable
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from lib import (
    AuthenticationObject,
    CheckBackend,
    CronExpression,
    CheckTemplateId,
    CheckId,
    Json,
    CheckTemplate,
    Check,
    MockBackend,
    NotFoundException,
)

# Dummy for now
auth_obj = AuthenticationObject("user1")
# Use type CheckBackend to ensure that the current backend could be replaced by any other without breaking anything
check_backend: CheckBackend = MockBackend()

app = FastAPI()


@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.get("/check_templates/")
## filter: conditions to filter on Metadata
async def list_check_templates(
    ids: Annotated[
        list[CheckTemplateId] | None, Query(description="restrict IDs to include")
    ] = None,
) -> Iterable[CheckTemplate]:
    return await check_backend.list_check_templates(ids)


@app.post("/checks")
async def new_check(
    template_id: CheckTemplateId,
    template_args: Json,
    schedule: CronExpression,
) -> CheckId:
    return await check_backend.new_check(auth_obj, template_id, template_args, schedule)


@app.patch("/checks/{check_id}")
async def update_check(
    check_id: CheckId,
    template_id: CheckTemplateId | None = None,
    template_args: Json = None,
    schedule: CronExpression | None = None,
) -> None:
    return await check_backend.update_check(
        auth_obj, check_id, template_id, template_args, schedule
    )


@app.delete("/checks/{check_id}")
async def remove_check(check_id: CheckId) -> None:
    return await check_backend.remove_check(auth_obj, check_id)


@app.get("/checks/")
async def list_checks(
    ids: Annotated[
        list[CheckId] | None, Query(description="restrict IDs to include")
    ] = None,
) -> Iterable[Check]:
    return await check_backend.list_checks(auth_obj, ids)


# This needs to be at the bottom so that all methods, error handlers, and such are already defined
with open("openapi.json", mode="w+") as file:
    json.dump(app.openapi(), file, indent=2)
