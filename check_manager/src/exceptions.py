from jsonschema import ValidationError
from eoepca_api_utils.exceptions import (
    APIException,
    APIForbiddenError,
    APIUserInputError,
)
from eoepca_api_utils.json_api_types import ErrorSourcePointer


class JsonValidationError(APIException):
    def __init__(self, path_start: str, e: ValidationError) -> None:
        """path_start is json pointer start to prepend"""
        super().__init__(
            status="422",
            title="Json is not valid for this schema",
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


class CronExpressionValidationError(APIUserInputError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            title="Cron expression is invalid",
            detail=detail,
        )


class NewCheckClientSpecifiedId(APIForbiddenError):
    def __init__(self) -> None:
        super().__init__(
            title="Client must not specify new check id",
            detail="Client must not specify new check id",
        )


class CheckConnectionError(APIException, ConnectionError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status="500",
            title="HTTP request failed",
            detail=detail,
        )
