from abc import ABC, abstractmethod
import asyncio
from collections import defaultdict
from enum import Enum, auto
from types import TracebackType
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


class ErrorCode(Enum):
    MainIdNotFound = auto()
    NotFound = auto()
    NonUniqueId = auto()
    InternalError = auto()


class CustomException(Exception):
    def __init__(self: Self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


ERROR_CODE_KEY: Final[str] = "code"
ERROR_MESSAGE_KEY: Final[str] = "detail"


def get_status_code_and_message(exception: BaseException) -> tuple[int, Json]:
    if not isinstance(exception, CustomException):
        exception = CustomException(ErrorCode.InternalError, "Internal server error")
    error_json: dict[str, object] = {
        ERROR_CODE_KEY: exception.code.name,
        ERROR_MESSAGE_KEY: str(exception),
    }
    match exception.code:
        case ErrorCode.MainIdNotFound | ErrorCode.NotFound:
            return (404, error_json)
        case ErrorCode.NonUniqueId | ErrorCode.InternalError:
            return (500, error_json)
        case unreachable:
            assert_never(unreachable)


def get_exception(status_code: int, content: Any) -> CustomException:
    error_code = ErrorCode[content[ERROR_CODE_KEY]]
    message: str = content[ERROR_MESSAGE_KEY]
    return CustomException(error_code, message)


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
    # Close connections, release resources and such
    # aclose is the standard name such methods when they are asynchronous
    @abstractmethod
    async def aclose(self: Self) -> None:
        pass

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

    # Raise CustomException with MainIdNotFound code if template_id doesn't exist.
    # Otherwise don't use that error code
    @abstractmethod
    async def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> Check:
        pass

    # Raise CustomException with MainIdNotFound code if check_id doesn't exist.
    # Otherwise don't use that error code
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

    # Raise CustomException with MainIdNotFound code if check_id doesn't exist.
    # Otherwise don't use that error code
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
    def __init__(self: Self, template_id_prefix: str = "") -> None:
        check_templates = [
            CheckTemplate(
                id=CheckTemplateId(template_id_prefix + "check_template1"),
                metadata={
                    "label": "Default Kubernetes template",
                    "description": "Default template for checks in the Kubernetes backend.",
                },
                arguments={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string"
                        },
                        "script": {
                            "type": "string",
                        },
                        "requirements": {
                            "type": "string",
                        },
                    },
                    "required": ["label", "script"],
                },
            ),
            CheckTemplate(
                id=CheckTemplateId(template_id_prefix + "check_template2"),
                metadata={
                    "label": "One more check template",
                    "description": "Blady bla",
                },
                arguments={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                        },
                        "requirements": {
                            "type": "string",
                        },
                        "file": {
                            "type": "string",
                            "format": "data-url"
                        }
                    },
                    "required": ["script"],
                },
            )
        ]
        self._check_template_id_to_template: dict[CheckTemplateId, CheckTemplate] = {
            template.id: template for template in check_templates
        }
        self._auth_to_id_to_check: defaultdict[
            AuthenticationObject, dict[CheckId, Check]
        ] = defaultdict(dict)

    @override
    async def aclose(self: Self) -> None:
        pass

    def _get_check_template(self: Self, template_id: CheckTemplateId) -> CheckTemplate:
        if template_id not in self._check_template_id_to_template:
            raise CustomException(
                ErrorCode.NotFound, f"Template id {template_id} not found"
            )
        return self._check_template_id_to_template[template_id]

    def _get_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> Check:
        id_to_check = self._auth_to_id_to_check[auth_obj]
        if check_id not in id_to_check:
            raise CustomException(ErrorCode.NotFound, f"Check id {check_id} not found")
        return id_to_check[check_id]

    @override
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

    @override
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

    @override
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

    @override
    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        id_to_check = self._auth_to_id_to_check[auth_obj]
        if check_id not in id_to_check:
            raise CustomException(ErrorCode.NotFound, f"Check id {check_id} not found")
        id_to_check.pop(check_id)

    @override
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
        self._client = httpx.AsyncClient()

    @override
    async def aclose(self: Self) -> None:
        await self._client.aclose()

    @override
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

    @override
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

    @override
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

    @override
    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        response = await self._client.delete(
            self._url + REMOVE_CHECK_PATH.format(check_id=check_id)
        )
        if response.is_success:
            return None
        raise get_exception(status_code=response.status_code, content=response.json())

    @override
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


class AggregationBackend(CheckBackend):
    def __init__(self, backends: list[CheckBackend]) -> None:
        self._backends = backends

    @staticmethod
    def _process_results[T](
        results: list[T | BaseException], non_unique_id_message: str
    ) -> T:
        successes = [
            result for result in results if not isinstance(result, BaseException)
        ]
        # Interesting failures.
        failures = [
            result
            for result in results
            if isinstance(result, Exception)
            and (
                not isinstance(result, CustomException)
                or result.code != ErrorCode.MainIdNotFound
            )
        ]
        match (successes, failures):
            case ([success], _):
                return success
            case ([_, _, *_], _):
                raise CustomException(ErrorCode.NonUniqueId, non_unique_id_message)
            case ([], [failure, *_]):
                raise failure
            case ([], []):
                assert isinstance(results[0], Exception)
                raise results[0]
            case _:
                # This is unreachable as far as I can tell, but Mypy doesn't agree.
                # It seems to have a problem with [*rest] type of patterns - it doesn't recognise that [*rest] would
                # match any list, for example
                assert False

    @override
    async def aclose(self: Self) -> None:
        await asyncio.gather(*(backend.aclose() for backend in self._backends))

    @override
    async def list_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        for backend in self._backends:
            async for template in backend.list_check_templates(ids):
                yield template

    @override
    async def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> Check:
        results = await asyncio.gather(
            *(
                backend.new_check(auth_obj, template_id, template_args, schedule)
                for backend in self._backends
            ),
            return_exceptions=True,
        )
        return AggregationBackend._process_results(
            results, f"Check template id {template_id} exists in multiple backends"
        )

    @override
    async def update_check(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
        template_id: CheckTemplateId | None = None,
        template_args: Json | None = None,
        schedule: CronExpression | None = None,
    ) -> Check:
        results = await asyncio.gather(
            *(
                backend.update_check(
                    auth_obj, check_id, template_id, template_args, schedule
                )
                for backend in self._backends
            ),
            return_exceptions=True,
        )
        return AggregationBackend._process_results(
            results, f"Check id {check_id} exists in multiple backends"
        )

    @override
    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        results = await asyncio.gather(
            *(backend.remove_check(auth_obj, check_id) for backend in self._backends),
            return_exceptions=True,
        )
        return AggregationBackend._process_results(
            results, f"Check id {check_id} exists in multiple backends"
        )

    @override
    async def list_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[Check]:
        # A trick to make the type of the function what I want
        # Why yield inside function body effects the type of the function is explained in
        # https://mypy.readthedocs.io/en/stable/more_types.html#asynchronous-iterators
        for backend in self._backends:
            async for check in backend.list_checks(auth_obj, ids):
                yield check


class CheckBackendContextManager:
    def __init__(self: Self, check_backend: CheckBackend) -> None:
        self._check_backend = check_backend

    async def __aenter__(self: Self) -> CheckBackend:
        return self._check_backend

    async def __aexit__(
        self: Self,
        exctype: Type[BaseException] | None,
        excinst: BaseException | None,
        exctb: TracebackType | None,
    ) -> Literal[False]:
        await self._check_backend.aclose()
        return False
