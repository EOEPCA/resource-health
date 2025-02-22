from typing import (
    Any,
    AsyncIterable,
    Final,
    Literal,
    NewType,
    Self,
    Type,
    assert_never,
    override,
)
import httpx
from pydantic import TypeAdapter

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
from check_backends.check_backend import (
    AuthenticationObject,
    CronExpression,
    CheckBackend,
    Check,
    CheckId,
    CheckTemplate,
    CheckTemplateId,
)

from exceptions import (
    CheckException,
    CheckInternalError,
    CheckIdError,
    CheckIdNonUniqueError,
    CheckConnectionError,
)


class RestBackend(CheckBackend):
    def __init__(self: Self, rest_url: str) -> None:
        self._url = rest_url
        self._client = httpx.AsyncClient()

    @override
    async def aclose(self: Self) -> None:
        await self._client.aclose()

    @override
    async def list_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        try:
            response = await self._client.get(
                self._url + LIST_CHECK_TEMPLATES_PATH,
                params={"ids": ids} if ids is not None else {},
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(e.args[0])
        if response.is_success:
            # using Iterable[CheckTemplate] here and trying to iterate over the result explodes for some reason
            for check_template in TypeAdapter(list[CheckTemplate]).validate_python(
                response.json()
            ):
                yield check_template
        else:
            raise get_exception(
                status_code=response.status_code, content=response.json()
            )

    @override
    async def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> Check:
        try:
            response = await self._client.post(
                self._url + NEW_CHECK_PATH,
                json={
                    "template_id": template_id,
                    "template_args": template_args,
                    "schedule": schedule,
                },
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(e.args[0])
        if response.is_success:
            return Check.model_validate(response.json())
        raise get_exception(status_code=response.status_code, content=response.json())

    # @override
    # async def update_check(
    #     self: Self,
    #     auth_obj: AuthenticationObject,
    #     check_id: CheckId,
    #     template_id: CheckTemplateId | None = None,
    #     template_args: Json | None = None,
    #     schedule: CronExpression | None = None,
    # ) -> Check:
    #     try:
    #         response = await self._client.patch(
    #             self._url + UPDATE_CHECK_PATH.format(check_id=check_id),
    #             json={
    #                 "template_id": template_id,
    #                 "template_args": template_args,
    #                 "schedule": schedule,
    #             },
    #         )
    #     except httpx.HTTPError as e:
    #         raise CheckConnectionError(e.args[0])
    #     if response.is_success:
    #         return Check.model_validate(response.json())
    #     raise get_exception(status_code=response.status_code, content=response.json())

    @override
    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        try:
            response = await self._client.delete(
                self._url + REMOVE_CHECK_PATH.format(check_id=check_id)
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(e.args[0])
        if response.is_success:
            return None
        raise get_exception(status_code=response.status_code, content=response.json())

    @override
    async def list_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[Check]:
        try:
            response = await self._client.get(
                self._url + LIST_CHECKS_PATH,
                params={"ids": ids} if ids is not None else {},
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(e.args[0])
        # TODO: stream this instead of accumulating everything first
        if response.is_success:
            for check in TypeAdapter(list[Check]).validate_python(response.json()):
                yield check
        else:
            raise get_exception(
                status_code=response.status_code, content=response.json()
            )
