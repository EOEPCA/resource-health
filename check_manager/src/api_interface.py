from typing import Final, Iterable
from urllib import parse
from fastapi import Request

from api_utils.exceptions import CheckInternalError
from check_backends.check_backend import (
    CheckIdError,
    CheckIdNonUniqueError,
    CheckTemplateIdError,
)
from exceptions import (
    CheckException,
    CheckConnectionError,
    JsonValidationError,
)
from api_utils.json_api_types import Error


ERROR_CODE_KEY: Final[str] = "error"
ERROR_MESSAGE_KEY: Final[str] = "detail"

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


def get_exception(error: Error) -> CheckException:
    match error.code:
        case JsonValidationError.__name__:
            return JsonValidationError(error)
        case CheckInternalError.__name__:
            return CheckInternalError(error)
        case CheckTemplateIdError.__name__:
            return CheckTemplateIdError(error)
        case CheckIdError.__name__:
            return CheckIdError(error)
        case CheckIdNonUniqueError.__name__:
            return CheckIdNonUniqueError(error)
        case CheckConnectionError.__name__:
            return CheckConnectionError(error)
        case _:
            return CheckException(error)


def get_request_url_str(base_url: str, request: Request) -> str:
    return _concat_url_str(base_url, request.url.path, request.url.query)


# Can't accept dict[str, str] for query params because the same key might have multiple values.
def get_url_str(
    base_url: str,
    path: str,
    path_params: dict[str, str] | None = None,
    query_params_list: Iterable[tuple[str, str]] | None = None,
) -> str:
    path_str = path.format_map(
        {
            parse.quote(key, safe=""): parse.quote(value, safe="")
            for key, value in (path_params or {}).items()
        }
    )
    return _concat_url_str(
        base_url, path_str, query=parse.urlencode(list(query_params_list or []))
    )


def _concat_url_str(base_url: str, path: str, query: str) -> str:
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    return base_url + path + ("?" + query if query else "")
