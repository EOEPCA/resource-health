from dataclasses import dataclass
from typing import Self

from jsonschema import ValidationError
from api_utils.json_api_types import Error, ErrorSourcePointer


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


class JsonValidationError(CheckException):
    """Json is not valid for this schema"""

    @classmethod
    def create(cls, path_start: str, e: ValidationError) -> Self:
        """path_start is json pointer start to prepend"""
        return cls(
            Error(
                status="422",
                code=cls._create_code(),
                title=cls._create_title_from_doc(),
                source=ErrorSourcePointer(
                    pointer=path_start + "/".join([str(name) for name in e.path])
                ),
                detail=str(e.message),
                meta={
                    # "path": [name for name in e.path],
                    "schema_path": [name for name in e.schema_path],
                    "context": e.context,
                    "cause": e.cause,
                    "validator": e.validator,
                    "validator_value": e.validator_value,
                    "instance": e.instance,
                    "schema": e.schema,
                },
            )
        )


class NewCheckClientSpecifiedId(CheckException):
    """Client must not specify new check id"""

    @classmethod
    def create(cls) -> Self:
        return cls(
            Error(
                status="403",
                code=cls._create_code(),
                title=cls._create_title_from_doc(),
                detail="Client must not specify new check id",
            )
        )


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


class CheckConnectionError(CheckException, ConnectionError):
    """HTTP request failed"""

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
