from typing import Any, Final

from api_utils.exceptions import APIExceptions, APIInternalError, get_exceptions
from check_backends.check_backend import (
    CheckIdError,
    CheckIdNonUniqueError,
    CheckTemplateIdError,
)
from exceptions import (
    APIException,
    CheckConnectionError,
    JsonValidationError,
    CronExpressionValidationError,
)
from api_utils.json_api_types import Error


ROUTE_PREFIX = "/v1"
GET_CHECK_TEMPLATES_PATH: Final[str] = ROUTE_PREFIX + "/check_templates/"
GET_CHECK_TEMPLATE_PATH: Final[str] = (
    ROUTE_PREFIX + "/check_templates/{check_template_id}"
)
CREATE_CHECK_PATH: Final[str] = ROUTE_PREFIX + "/checks/"
GET_CHECK_PATH: Final[str] = ROUTE_PREFIX + "/checks/{check_id}"
UPDATE_CHECK_PATH: Final[str] = ROUTE_PREFIX + "/checks/{check_id}"
REMOVE_CHECK_PATH: Final[str] = ROUTE_PREFIX + "/checks/{check_id}"
GET_CHECKS_PATH: Final[str] = ROUTE_PREFIX + "/checks/"
RUN_CHECK_PATH: Final[str] = ROUTE_PREFIX + "/checks/{check_id}/run/"


def get_check_exceptions(
    status_code: int, content: dict[str, Any]
) -> APIException | APIExceptions:
    return get_exceptions(_get_exception, status_code, content)


def _get_exception(error: Error) -> APIException:
    match error.code:
        case JsonValidationError.__name__:
            return JsonValidationError(error)
        case CronExpressionValidationError.__name__:
            return CronExpressionValidationError(error)
        case APIInternalError.__name__:
            return APIInternalError(error)
        case CheckTemplateIdError.__name__:
            return CheckTemplateIdError(error)
        case CheckIdError.__name__:
            return CheckIdError(error)
        case CheckIdNonUniqueError.__name__:
            return CheckIdNonUniqueError(error)
        case CheckConnectionError.__name__:
            return CheckConnectionError(error)
        case _:
            return APIException(error)
