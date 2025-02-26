from dataclasses import dataclass
from typing import Any, Callable, Self

from api_utils.json_api_types import APIErrorResponse, Error


@dataclass
class CheckException(Exception):
    """Base exception class"""

    error: Error

    @classmethod
    def _create_code(cls) -> str:
        return cls.__name__

    @classmethod
    def _create_title_from_doc(cls) -> str:
        return cls.__doc__ or ""


@dataclass
class CheckExceptions(Exception):
    # HTTP status code
    status: int
    exceptions: list[CheckException]


class CheckInternalError(CheckException):
    """Check internal error"""

    @classmethod
    def create(cls, detail: str) -> Self:
        return cls(
            Error(
                status="500",
                code=cls._create_code(),
                title=cls._create_title_from_doc(),
                detail=detail,
            )
        )


def get_status_code_and_errors(exception: Exception) -> tuple[int, list[Error]]:
    match exception:
        case CheckExceptions():
            exceptions = exception
        case CheckException():
            exceptions = CheckExceptions(
                status=int(exception.error.status), exceptions=[exception]
            )
        case _:
            exceptions = CheckExceptions(
                status=500,
                exceptions=[CheckInternalError.create("Internal server error")],
            )
    return exceptions.status, [exc.error for exc in exceptions.exceptions]


def get_exceptions(
    get_exception: Callable[[Error], CheckException],
    status_code: int,
    content: dict[str, Any],
) -> CheckException | CheckExceptions:
    error_response = APIErrorResponse.model_validate(content)
    exceptions = [get_exception(error) for error in error_response.errors]
    if len(exceptions) == 1:
        return exceptions[0]
    else:
        return CheckExceptions(status=status_code, exceptions=exceptions)
