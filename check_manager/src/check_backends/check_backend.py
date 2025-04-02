from abc import ABC, abstractmethod
import asyncio
from types import TracebackType
from typing import (
    AsyncIterable,
    Generic,
    TypeVar,
    Literal,
    NewType,
    Self,
    Type,
    override,
)
from pydantic import BaseModel, TypeAdapter
from referencing.jsonschema import Schema

from exceptions import APIException
from api_utils.json_api_types import Error, Json

AuthenticationObject = TypeVar("AuthenticationObject")

CronExpression = NewType("CronExpression", str)
CheckTemplateId = NewType("CheckTemplateId", str)
CheckId = NewType("CheckId", str)


class CheckTemplateIdError(APIException, KeyError):
    """Template Id not found"""

    @classmethod
    def create(cls, check_template_id: CheckTemplateId) -> Self:
        return cls(
            Error(
                status="404",
                code=cls._create_code(),
                title=cls._create_title_from_doc(),
                detail=f"Check template id {check_template_id} not found",
            )
        )


class CheckIdError(APIException, KeyError):
    """Check Id not found"""

    @classmethod
    def create(cls, check_id: CheckId) -> Self:
        return cls(
            Error(
                status="404",
                code=cls._create_code(),
                title=cls._create_title_from_doc(),
                detail=f"Check id {check_id} not found",
            )
        )


class CheckIdNonUniqueError(APIException, KeyError):
    """Check Id is not unique"""

    @classmethod
    def create(cls, check_id: CheckId) -> Self:
        return cls.create_with_detail(f"Check id {check_id} is not unique")

    @classmethod
    def create_with_detail(cls, detail: str) -> Self:
        return cls(
            Error(
                status="400",
                code=cls._create_code(),
                title=cls._create_title_from_doc(),
                detail=detail,
            )
        )


class CheckTemplateMetadata(BaseModel, extra="allow"):
    label: str | None
    description: str | None


class CheckTemplateAttributes(BaseModel):
    metadata: CheckTemplateMetadata
    arguments: Schema


class CheckTemplate(BaseModel):
    id: CheckTemplateId
    attributes: CheckTemplateAttributes


class InCheckMetadata(BaseModel):
    # SHOULD have name and description
    name: str
    description: str
    # MAY have template_id and template_args
    template_id: CheckTemplateId
    template_args: Json


class OutCheckMetadata(BaseModel, extra="allow"):
    # SHOULD have name and description
    name: str | None = None
    description: str | None = None
    # MAY have template_id and template_args
    template_id: CheckTemplateId | None = None
    template_args: Json | None = None


class InCheckAttributes(BaseModel):
    metadata: InCheckMetadata
    schedule: CronExpression


type TelemetryAttributes = dict[str, str | int | bool]


class OutcomeFilter(BaseModel):
    resource_attributes: TelemetryAttributes | None = None
    scope_attributes: TelemetryAttributes | None = None
    span_attributes: TelemetryAttributes | None = None


class OutCheckAttributes(BaseModel):
    metadata: OutCheckMetadata
    schedule: CronExpression
    # Conditions to determine which spans belong to this check outcome
    outcome_filter: OutcomeFilter
    ## NOTE: For now the above can just be a set of equality conditions on Span/Resource attributes


class InCheckData(BaseModel):
    type: str = "check"
    attributes: InCheckAttributes


class OutCheck(BaseModel):
    id: CheckId
    attributes: OutCheckAttributes


class InCheck(BaseModel):
    data: InCheckData


# Inherit from this class and implement the abstract methods for each new backend
class CheckBackend(ABC, Generic[AuthenticationObject]):
    # Close connections, release resources and such
    # aclose is the standard name such methods when they are asynchronous
    @abstractmethod
    async def aclose(self: Self) -> None:
        pass

    @abstractmethod
    async def get_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        # A trick to make the type of the function what I want
        # Why yield inside function body effects the type of the function is explained in
        # https://mypy.readthedocs.io/en/stable/more_types.html#asynchronous-iterators
        if False:
            yield

    # Raise CheckIdError if template_id doesn't exist.
    # Otherwise don't use that error code
    @abstractmethod
    async def create_check(
        self: Self, auth_obj: AuthenticationObject, attributes: InCheckAttributes
    ) -> OutCheck:
        pass

    # # Raise CheckIdError if check_id doesn't exist.
    # # Otherwise don't use that error code
    # @abstractmethod
    # async def update_check(
    #     self: Self,
    #     auth_obj: AuthenticationObject,
    #     check_id: CheckId,
    #     template_id: CheckTemplateId | None = None,
    #     template_args: Json | None = None,
    #     schedule: CronExpression | None = None,
    # ) -> Check:
    #     pass

    # Raise CheckIdError if check_id doesn't exist.
    # Otherwise don't use that error code
    @abstractmethod
    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        pass

    @abstractmethod
    async def get_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[OutCheck]:
        # A trick to make the type of the function what I want
        # Why yield inside function body effects the type of the function is explained in
        # https://mypy.readthedocs.io/en/stable/more_types.html#asynchronous-iterators
        if False:
            yield

    # Raise CheckIdError if check_id doesn't exist.
    # Otherwise don't use that error code
    @abstractmethod
    async def run_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        pass


class AggregationBackend(CheckBackend[AuthenticationObject]):
    def __init__(self, backends: list[CheckBackend]) -> None:
        self._backends = backends

    @staticmethod
    def _process_results[T](
        results: list[T | BaseException], non_unique_id_message: str
    ) -> T:
        successes = [
            result for result in results if not isinstance(result, BaseException)
        ]
        # Interesting failures. (i.e. all exceptions that are not MainIdNotFound)
        failures = [
            result
            for result in results
            if isinstance(result, Exception) and not isinstance(result, CheckIdError)
        ]

        match (successes, failures):
            case ([success], _):
                return success
            case ([_, _, *_], _):
                raise CheckIdNonUniqueError.create_with_detail(non_unique_id_message)
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
    async def get_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        for backend in self._backends:
            async for template in backend.get_check_templates(ids):
                yield template

    @override
    async def create_check(
        self: Self, auth_obj: AuthenticationObject, attributes: InCheckAttributes
    ) -> OutCheck:
        index: int = TypeAdapter(int).validate_python(
            attributes.metadata.template_args.pop("service_index", 0)
        )
        return await self._backends[index].create_check(auth_obj, attributes)
        # results = await asyncio.gather(
        #     *(
        #         backend.new_check(auth_obj, template_id, template_args, schedule)
        #         for backend in self._backends
        #     ),
        #     return_exceptions=True,
        # )
        # return AggregationBackend._process_results(
        #     results, f"Check template id {template_id} exists in multiple backends"
        # )

    # @override
    # async def update_check(
    #     self: Self,
    #     auth_obj: AuthenticationObject,
    #     check_id: CheckId,
    #     template_id: CheckTemplateId | None = None,
    #     template_args: Json | None = None,
    #     schedule: CronExpression | None = None,
    # ) -> Check:
    #     results = await asyncio.gather(
    #         *(
    #             backend.update_check(
    #                 auth_obj, check_id, template_id, template_args, schedule
    #             )
    #             for backend in self._backends
    #         ),
    #         return_exceptions=True,
    #     )
    #     return AggregationBackend._process_results(
    #         results, f"Check id {check_id} exists in multiple backends"
    #     )

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
    async def get_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[OutCheck]:
        for backend in self._backends:
            async for check in backend.get_checks(auth_obj, ids):
                yield check

    @override
    async def run_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        results = await asyncio.gather(
            *(backend.run_check(auth_obj, check_id) for backend in self._backends),
            return_exceptions=True,
        )
        return AggregationBackend._process_results(
            results, f"Check id {check_id} exists in multiple backends"
        )


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
