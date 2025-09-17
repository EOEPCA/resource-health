from typing import (
    AsyncIterable,
    Self,
    override,
)
import httpx

from api_interface import (
    GET_CHECK_TEMPLATES_PATH,
    GET_CHECKS_PATH,
    CREATE_CHECK_PATH,
    REMOVE_CHECK_PATH,
    RUN_CHECK_PATH,
    get_check_exceptions,
)
from eoepca_api_utils.api_utils import get_url_str
from check_backends.check_backend import (
    AuthenticationObject,
    CheckBackend,
    CheckId,
    CheckTemplate,
    CheckTemplateId,
    CheckTemplateAttributes,
    InCheck,
    InCheckAttributes,
    InCheckData,
    OutCheck,
    OutCheckAttributes,
)

from exceptions import CheckConnectionError
from eoepca_api_utils.json_api_types import APIOKResponse, APIOKResponseList


class RestBackend(CheckBackend[AuthenticationObject]):
    def __init__(self: Self, rest_url: str) -> None:
        self._url = rest_url
        self._client = httpx.AsyncClient()

    @override
    async def aclose(self: Self) -> None:
        await self._client.aclose()

    @override
    async def get_check_templates(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        try:
            response = await self._client.get(
                get_url_str(self._url, GET_CHECK_TEMPLATES_PATH),
                params={"ids": ids} if ids is not None else {},
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(str(e))
        if response.is_success:
            for check_template in (
                APIOKResponseList[CheckTemplateAttributes, None]
                .model_validate(response.json())
                .data
            ):
                yield CheckTemplate(
                    id=CheckTemplateId(check_template.id),
                    attributes=check_template.attributes,
                )
        else:
            raise get_check_exceptions(
                status_code=response.status_code, content=response.json()
            )

    @override
    async def create_check(
        self: Self, auth_obj: AuthenticationObject, attributes: InCheckAttributes
    ) -> OutCheck:
        try:
            response = await self._client.post(
                get_url_str(self._url, CREATE_CHECK_PATH),
                json=InCheck(data=InCheckData(attributes=attributes)).model_dump(
                    exclude_unset=True
                ),
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(str(e))
        if response.is_success:
            structured_response = APIOKResponse[OutCheckAttributes].model_validate(
                response.json()
            )
            return OutCheck(
                id=CheckId(structured_response.data.id),
                attributes=structured_response.data.attributes,
            )
        else:
            raise get_check_exceptions(
                status_code=response.status_code, content=response.json()
            )

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
    #         raise CheckConnectionError(str(e))
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
            raise CheckConnectionError(str(e))
        if response.is_success:
            return None
        raise get_check_exceptions(
            status_code=response.status_code, content=response.json()
        )

    @override
    async def get_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[OutCheck]:
        try:
            response = await self._client.get(
                get_url_str(self._url, GET_CHECKS_PATH),
                params={"ids": ids} if ids is not None else {},
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(str(e))
        # TODO: stream this instead of accumulating everything first
        if response.is_success:
            for check in (
                APIOKResponseList[OutCheckAttributes, None]
                .model_validate(response.json())
                .data
            ):
                yield OutCheck(id=CheckId(check.id), attributes=check.attributes)
        else:
            raise get_check_exceptions(
                status_code=response.status_code, content=response.json()
            )

    @override
    async def run_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        try:
            response = await self._client.post(
                get_url_str(
                    self._url, RUN_CHECK_PATH, path_params={"check_id": check_id}
                )
            )
        except httpx.HTTPError as e:
            raise CheckConnectionError(str(e))
        if response.is_success:
            return None
        raise get_check_exceptions(
            status_code=response.status_code, content=response.json()
        )
