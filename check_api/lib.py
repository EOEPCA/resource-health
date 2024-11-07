from abc import ABC, abstractmethod
from collections import defaultdict
from types import TracebackType
from typing import Any, AsyncIterable, Final, Literal, NewType, Self, Type
import uuid
import httpx
from jsonschema import validate
from pydantic import BaseModel, TypeAdapter
from referencing.jsonschema import Schema

AuthenticationObject = NewType("AuthenticationObject", str)
CronExpression = NewType("CronExpression", str)
CheckTemplateId = NewType("CheckTemplateId", str)
CheckId = NewType("CheckId", str)
type Json = dict[str, object]


class NotFoundException(Exception):
    pass


ERROR_MESSAGE_KEY: Final[str] = "detail"


def get_status_code_and_message(exception: Exception) -> tuple[int, Json]:
    match exception:
        case NotFoundException():
            return (404, {ERROR_MESSAGE_KEY: str(exception)})
        case Exception():
            return (500, {ERROR_MESSAGE_KEY: "Internal server error"})


def get_exception(status_code: int, content: Any) -> Exception:
    message: str = content[ERROR_MESSAGE_KEY]
    match status_code:
        case 403:
            return NotFoundException(message)
        case _:
            return Exception(message)


class CheckTemplate(BaseModel):
    id: CheckTemplateId
    # SHOULD contain { 'label' : str, 'description' : str }
    metadata: Json
    arguments: Schema


class Check(BaseModel):
    id: CheckId
    # SHOULD contain { 'label' : str, 'description' : str }, MAY contain { 'template': CheckTemplate, 'template_args': Json }
    metadata: Json
    schedule: CronExpression

    # Conditions to determine which spans belong to this check outcome
    outcome_filter: Json
    ## NOTE: For now the above can just be a set of equality conditions on Span/Resource attributes


# Inherit from this class and implement the abstract methods for each new backend
class CheckBackend(ABC):
    @abstractmethod
    async def list_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        # A trick to make the type of the function what I want
        # Why yield inside function body effects the type of the function is explained in
        # https://mypy.readthedocs.io/en/stable/more_types.html#asynchronous-iterators
        if False:
            yield

    @abstractmethod
    async def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> Check:
        pass

    @abstractmethod
    async def update_check(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
        template_id: CheckTemplateId | None = None,
        template_args: Json | None = None,
        schedule: CronExpression | None = None,
    ) -> Check:
        pass

    @abstractmethod
    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        pass

    @abstractmethod
    async def list_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[Check]:
        # A trick to make the type of the function what I want
        # Why yield inside function body effects the type of the function is explained in
        # https://mypy.readthedocs.io/en/stable/more_types.html#asynchronous-iterators
        if False:
            yield


class MockBackend(CheckBackend):
    def __init__(self: Self) -> None:
        check_templates = [
            CheckTemplate(
                id=CheckTemplateId("check_template1"),
                metadata={
                    "label": "Dummy check template",
                    "description": "Dummy check template description",
                },
                arguments={
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "title": "Bla",
                    "description": "Bla bla",
                    # TODO: continue this
                    # "type": "object",
                    # "properties": "",
                },
            )
        ]
        self._check_template_id_to_template: dict[CheckTemplateId, CheckTemplate] = {
            template.id: template for template in check_templates
        }
        self._auth_to_id_to_check: defaultdict[
            AuthenticationObject, dict[CheckId, Check]
        ] = defaultdict(dict)

    def _get_check_template(self: Self, template_id: CheckTemplateId) -> CheckTemplate:
        if template_id not in self._check_template_id_to_template:
            raise NotFoundException(f"Template id {template_id} not found")
        return self._check_template_id_to_template[template_id]

    def _get_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> Check:
        id_to_check = self._auth_to_id_to_check[auth_obj]
        if check_id not in id_to_check:
            raise NotFoundException(f"Check id {check_id} not found")
        return id_to_check[check_id]

    async def list_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        if ids is None:
            for template in self._check_template_id_to_template.values():
                yield template
        else:
            for id in ids:
                yield self._get_check_template(id)

    async def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> Check:
        check_template = self._get_check_template(template_id)
        validate(template_args, check_template.arguments)
        check_id = CheckId(str(uuid.uuid4()))
        check = Check(
            id=check_id,
            metadata={"template_id": template_id, "template_args": template_args},
            schedule=schedule,
            outcome_filter={"test.id": check_id},
        )
        self._auth_to_id_to_check[auth_obj][check_id] = check
        return check

    async def update_check(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
        template_id: CheckTemplateId | None = None,
        template_args: Json | None = None,
        schedule: CronExpression | None = None,
    ) -> Check:
        check = self._get_check(auth_obj, check_id)
        if template_id is not None:
            check.metadata["template_id"] = template_id
        if template_args is not None:
            check.metadata["template_args"] = template_args
        # TODO: check check if template_args and check_template are compatible
        if schedule is not None:
            check.schedule = schedule
        return check

    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        id_to_check = self._auth_to_id_to_check[auth_obj]
        if check_id not in id_to_check:
            raise NotFoundException(f"Check id {check_id} not found")
        id_to_check.pop(check_id)

    async def list_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[Check]:
        if ids is None:
            for check in self._auth_to_id_to_check[auth_obj].values():
                yield check
        else:
            for id in ids:
                yield self._get_check(auth_obj, id)


LIST_CHECK_TEMPLATES_PATH: Final[str] = "/check_templates/"
NEW_CHECK_PATH: Final[str] = "/checks/"
UPDATE_CHECK_PATH: Final[str] = "/checks/{check_id}"
REMOVE_CHECK_PATH: Final[str] = "/checks/{check_id}"
LIST_CHECKS_PATH: Final[str] = "/checks/"


class RestBackend(CheckBackend):
    def __init__(self: Self, rest_url: str) -> None:
        self._url = rest_url

    async def __aenter__(self: Self) -> Self:
        self._client = httpx.AsyncClient()
        return self

    async def __aexit__(
        self: Self,
        exctype: Type[BaseException] | None,
        excinst: BaseException | None,
        exctb: TracebackType | None,
    ) -> Literal[False]:
        await self._client.aclose()
        return False

    async def list_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        response = await self._client.get(
            self._url + LIST_CHECK_TEMPLATES_PATH,
            params={"ids": ids} if ids is not None else {},
        )
        # TODO: stream this instead of accumulating everything first
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

    async def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> Check:
        response = await self._client.post(
            self._url + NEW_CHECK_PATH,
            json={
                "template_id": template_id,
                "template_args": template_args,
                "schedule": schedule,
            },
        )
        if response.is_success:
            return Check.model_validate(response.json())
        raise get_exception(status_code=response.status_code, content=response.json())

    async def update_check(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
        template_id: CheckTemplateId | None = None,
        template_args: Json | None = None,
        schedule: CronExpression | None = None,
    ) -> Check:
        response = await self._client.patch(
            self._url + UPDATE_CHECK_PATH.format(check_id=check_id),
            json={
                "template_id": template_id,
                "template_args": template_args,
                "schedule": schedule,
            },
        )
        if response.is_success:
            return Check.model_validate(response.json())
        raise get_exception(status_code=response.status_code, content=response.json())

    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        response = await self._client.delete(
            self._url + REMOVE_CHECK_PATH.format(check_id=check_id)
        )
        if response.is_success:
            return None
        raise get_exception(status_code=response.status_code, content=response.json())

    async def list_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[Check]:
        response = await self._client.get(
            self._url + LIST_CHECKS_PATH, params={"ids": ids} if ids is not None else {}
        )
        # TODO: stream this instead of accumulating everything first
        if response.is_success:
            for check in TypeAdapter(list[Check]).validate_python(response.json()):
                yield check
        else:
            raise get_exception(
                status_code=response.status_code, content=response.json()
            )
