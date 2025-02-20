from typing import (
    AsyncIterable,
    Self,
    override,
)
import httpx

from api_interface import (
    LIST_CHECK_TEMPLATES_PATH,
    LIST_CHECKS_PATH,
    NEW_CHECK_PATH,
    REMOVE_CHECK_PATH,
    get_exception,
    get_url_str,
)
from check_backends.check_backend import (
    AuthenticationObject,
    CheckBackend,
    CheckId,
    CheckTemplateId,
    CheckTemplateAttributes,
    InCheck,
    InCheckAttributes,
    InCheckData,
    OutCheckAttributes,
)

from exceptions import CheckConnectionError
from json_api_types import APIOKResponse, APIOKResponseList


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
    ) -> AsyncIterable[tuple[CheckTemplateId, CheckTemplateAttributes]]:
        try:
            response = await self._client.get(
                get_url_str(self._url, LIST_CHECK_TEMPLATES_PATH),
                params={"id": ids} if ids is not None else {},
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(e.args[0])
        if response.is_success:
            for check_template in (
                APIOKResponseList[CheckTemplateAttributes]
                .model_validate(response.json())
                .data
            ):
                yield (CheckTemplateId(check_template.id), check_template.attributes)
        else:
            raise get_exception(
                status_code=response.status_code, content=response.json()
            )

    @override
    async def new_check(
        self: Self, auth_obj: AuthenticationObject, attributes: InCheckAttributes
    ) -> tuple[CheckId, OutCheckAttributes]:
        try:
            response = await self._client.post(
                get_url_str(self._url, NEW_CHECK_PATH),
                json=InCheck(data=InCheckData(attributes=attributes)).model_dump(
                    exclude_unset=True
                ),
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(e.args[0])
        if response.is_success:
            structured_response = APIOKResponse[OutCheckAttributes].model_validate(
                response.json()
            )
            return CheckId(
                structured_response.data.id
            ), structured_response.data.attributes
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
    #             get_url_str(self._url, UPDATE_CHECK_PATH, path_params={"check_id": check_id})),
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
                get_url_str(
                    self._url, REMOVE_CHECK_PATH, path_params={"check_id": check_id}
                )
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
    ) -> AsyncIterable[tuple[CheckId, OutCheckAttributes]]:
        try:
            response = await self._client.get(
                get_url_str(self._url, LIST_CHECKS_PATH),
                params={"id": ids} if ids is not None else {},
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(e.args[0])
        # TODO: stream this instead of accumulating everything first
        if response.is_success:
            for check in (
                APIOKResponseList[OutCheckAttributes]
                .model_validate(response.json())
                .data
            ):
                yield CheckId(check.id), check.attributes
        else:
            raise get_exception(
                status_code=response.status_code, content=response.json()
            )
