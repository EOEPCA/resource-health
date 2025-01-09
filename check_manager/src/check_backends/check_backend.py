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
from jsonschema import validate
from pydantic import BaseModel, TypeAdapter
from referencing.jsonschema import Schema

from api_interface import (
    Json,
)
from exceptions import (
    CheckException,
    CheckInternalError,
    CheckIdError,
    CheckIdNonUniqueError,
)

AuthenticationObject = NewType("AuthenticationObject", str)
CronExpression = NewType("CronExpression", str)
CheckTemplateId = NewType("CheckTemplateId", str)
CheckId = NewType("CheckId", str)


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

    # Raise CheckIdError if template_id doesn't exist.
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

    # Raise CheckIdError if check_id doesn't exist.
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

    # Raise CheckIdError if check_id doesn't exist.
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
                raise CheckIdNonUniqueError(non_unique_id_message)
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
        index: int = TypeAdapter(int).validate_python(
            template_args.pop("service_index", 0)
        )
        return await self._backends[index].new_check(
            auth_obj, template_id, template_args, schedule
        )
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
