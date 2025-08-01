from jsonschema import ValidationError
from api_utils.exceptions import APIException, APIForbiddenError
from api_utils.json_api_types import ErrorSourcePointer


class JsonValidationError(APIException):
    """Json is not valid for this schema"""

    def __init__(self, path_start: str, e: ValidationError) -> None:
        """path_start is json pointer start to prepend"""
        super().__init__(
            status="422",
            title=JsonValidationError._create_title_from_doc(),
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


class CronExpressionValidationError(APIException):
    """Cron expression is invalid"""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status="422",
            title=CronExpressionValidationError._create_title_from_doc(),
            detail=detail,
        )


class NewCheckClientSpecifiedId(APIForbiddenError):
    """Client must not specify new check id"""

    def __init__(self) -> None:
        super().__init__(
            title=NewCheckClientSpecifiedId._create_title_from_doc(),
            detail="Client must not specify new check id",
        )


class CheckConnectionError(APIException, ConnectionError):
    """HTTP request failed"""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status="500",
            title=CheckConnectionError._create_title_from_doc(),
            detail=detail,
        )
