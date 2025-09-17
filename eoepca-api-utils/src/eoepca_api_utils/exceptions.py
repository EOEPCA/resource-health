from dataclasses import dataclass
from typing import Any, Callable, Self

from pydantic import Json

from eoepca_api_utils.json_api_types import APIErrorResponse, Error, ErrorSource


class APIException(Exception):
    """
    Base exception class.
    These errors (and their provided details) are reported to the user, so be careful.
    """

    @classmethod
    def create(cls, error: Error) -> Self:
        # A hack to not call __init__ as I don't know how many and what arguments
        # that would expect in the derived classes
        exception = cls.__new__(cls)
        exception.error = error
        return exception

    def __init__(
        self,
        status: str,
        title: str,
        detail: str,
        code: str | None = None,
        source: ErrorSource | None = None,
        meta: Json | None = None,
    ) -> None:
        super().__init__(detail)
        self.error = Error(
            status=status,
            code=type(self).__name__ if code is None else code,
            title=title,
            detail=detail,
            source=source,
            meta=meta,
        )

    # This is used when exception is printed
    def __str__(self: Self) -> str:
        if self.error.detail:
            return self.error.detail
        if self.error.title:
            return self.error.title
        return self.error.code


@dataclass
class APIExceptions(Exception):
    # HTTP status code
    status: int
    exceptions: list[APIException]


class APIInternalError(APIException):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status="500",
            title="API internal error",
            detail=detail,
        )


class APIForbiddenError(APIException):
    def __init__(self, title: str, detail: str) -> None:
        super().__init__(status="403", title=title, detail=detail)


class APIUnauthorizedError(APIException):
    def __init__(self, title: str, detail: str) -> None:
        super().__init__(
            status="401",
            title=title,
            detail=detail,
        )


class APIUserInputError(APIException):
    def __init__(self, title: str, detail: str) -> None:
        super().__init__(status="422", title=title, detail=detail)


def get_status_code_and_errors(exception: Exception) -> tuple[int, list[Error]]:
    match exception:
        case APIExceptions():
            exceptions = exception
        case APIException():
            exceptions = APIExceptions(
                status=int(exception.error.status), exceptions=[exception]
            )
        case _:
            exceptions = APIExceptions(
                status=500,
                exceptions=[APIInternalError("Internal server error")],
            )
    return exceptions.status, [exc.error for exc in exceptions.exceptions]


def get_exceptions(
    get_exception: Callable[[Error], APIException],
    status_code: int,
    content: dict[str, Any],
) -> APIException | APIExceptions:
    error_response = APIErrorResponse.model_validate(content)
    exceptions = [get_exception(error) for error in error_response.errors]
    if len(exceptions) == 1:
        return exceptions[0]
    else:
        return APIExceptions(status=status_code, exceptions=exceptions)
