from functools import partial
import json
import time
from typing import (
    Annotated,
    AsyncIterable,
    Awaitable,
    Callable,
    Iterable,
    Mapping,
)
import anyio
from fastapi import Body, FastAPI, Path, Query, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from starlette.types import Receive, Scope, Send

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
    Check,
    MockBackend,
    get_status_code_and_message,
)


class StreamingJsonResponse(Response):
    type Item = BaseModel
    body_iterator: AsyncIterable[Item]

    def __init__(
        self,
        content: AsyncIterable[Item],
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.body_iterator = content
        self.status_code = status_code
        self.media_type = "application/json"
        self.background = None
        self.init_headers(headers)

    async def listen_for_disconnect(self, receive: Receive) -> None:
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                break

    async def stream_response(self, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )
        async for chunk in self.body_iterator:
            await send(
                {
                    "type": "http.response.body",
                    "body": chunk.model_dump_json().encode(),
                    "more_body": True,
                }
            )

        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async with anyio.create_task_group() as task_group:

            async def wrap(func: Callable[[], Awaitable[None]]) -> None:
                await func()
                task_group.cancel_scope.cancel()

            task_group.start_soon(wrap, partial(self.stream_response, send))
            await wrap(partial(self.listen_for_disconnect, receive))

        if self.background is not None:
            await self.background()


# class StreamingJsonResponse[Item: BaseModel](Response):
#     body_iterator: AsyncIterable[Item]

#     def __init__(
#         self,
#         content: AsyncIterable[Item],
#         status_code: int = 200,
#         headers: Mapping[str, str] | None = None,
#     ) -> None:
#         self.body_iterator = content
#         self.status_code = status_code
#         self.media_type = "application/json"
#         self.init_headers(headers)

#     async def listen_for_disconnect(self, receive: Receive) -> None:
#         while True:
#             message = await receive()
#             if message["type"] == "http.disconnect":
#                 break

#     async def stream_response(self, send: Send) -> None:
#         await send(
#             {
#                 "type": "http.response.start",
#                 "status": self.status_code,
#                 "headers": self.raw_headers,
#             }
#         )
#         async for chunk in self.body_iterator:
#             await send(
#                 {
#                     "type": "http.response.body",
#                     "body": chunk.model_dump_json(),
#                     "more_body": True,
#                 }
#             )

#         await send({"type": "http.response.body", "body": b"", "more_body": False})

#     async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
#         async with anyio.create_task_group() as task_group:

#             async def wrap(func: Callable[[], Awaitable[None]]) -> None:
#                 await func()
#                 task_group.cancel_scope.cancel()

#             task_group.start_soon(wrap, partial(self.stream_response, send))
#             await wrap(partial(self.listen_for_disconnect, receive))

#         if self.background is not None:
#             await self.background()

# [Item: BaseModel]
# THIS model gives interesting error. Could use that error to create a better model perhaps
# Item = TypeVar("Item")


# class StreamingJsonResponse(Response, BaseModel, Generic[Item]):
#     body_iterator: AsyncIterable[Item]

#     def __init__(
#         self,
#         content: AsyncIterable[Item],
#         status_code: int = 200,
#         headers: Mapping[str, str] | None = None,
#     ) -> None:
#         self.body_iterator = content
#         self.status_code = status_code
#         self.media_type = "application/json"
#         self.init_headers(headers)

#     async def listen_for_disconnect(self, receive: Receive) -> None:
#         while True:
#             message = await receive()
#             if message["type"] == "http.disconnect":
#                 break

#     async def stream_response(self, send: Send) -> None:
#         await send(
#             {
#                 "type": "http.response.start",
#                 "status": self.status_code,
#                 "headers": self.raw_headers,
#             }
#         )
#         async for chunk in self.body_iterator:
#             await send(
#                 {
#                     "type": "http.response.body",
#                     "body": chunk.model_dump_json(),
#                     "more_body": True,
#                 }
#             )

#         await send({"type": "http.response.body", "body": b"", "more_body": False})

#     async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
#         async with anyio.create_task_group() as task_group:

#             async def wrap(func: Callable[[], Awaitable[None]]) -> None:
#                 await func()
#                 task_group.cancel_scope.cancel()

#             task_group.start_soon(wrap, partial(self.stream_response, send))
#             await wrap(partial(self.listen_for_disconnect, receive))

#         if self.background is not None:
#             await self.background()


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


@app.get("/dummy", status_code=status.HTTP_200_OK)
async def get_dummy() -> StreamingResponse:
    def generator() -> Iterable[bytes]:
        yield b"["
        for i in range(10):
            time.sleep(1)
            yield f"""{"" if i == 0 else ","}{{"hel""".encode()
            yield f"""lo": "there {i}"}}""".encode()
        yield b"]"

    return StreamingResponse(generator())


@app.get(LIST_CHECK_TEMPLATES_PATH, status_code=status.HTTP_200_OK)
## filter: conditions to filter on Metadata
async def list_check_templates(
    ids: Annotated[
        list[CheckTemplateId] | None, Query(description="restrict IDs to include")
    ] = None,
) -> StreamingJsonResponse:  # StreamingResponse:
    # TODO: stream this instead of accumulating everything first
    return StreamingJsonResponse(check_backend.list_check_templates(ids))
    # return [
    #     check_template
    #     async for check_template in check_backend.list_check_templates(ids)
    # ]


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
) -> StreamingJsonResponse:  # StreamingResponse:
    # TODO: stream this instead of accumulating everything first
    return StreamingJsonResponse(check_backend.list_checks(auth_obj, ids))
    # return [check async for check in check_backend.list_checks(auth_obj, ids)]


# This needs to be at the bottom so that all methods, error handlers, and such are already defined
with open("openapi.json", mode="w+") as file:
    json.dump(app.openapi(), file, indent=2)
