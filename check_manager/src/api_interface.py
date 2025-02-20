from typing import Any, Final
from urllib import parse

from exceptions import (
    CheckException,
    CheckInternalError,
    CheckTemplateIdError,
    CheckIdError,
    CheckIdNonUniqueError,
    CheckConnectionError,
)


ERROR_CODE_KEY: Final[str] = "error"
ERROR_MESSAGE_KEY: Final[str] = "detail"

ROUTE_PREFIX = "/v1"
LIST_CHECK_TEMPLATES_PATH: Final[str] = ROUTE_PREFIX + "/check_templates/"
GET_CHECK_TEMPLATE_PATH: Final[str] = (
    ROUTE_PREFIX + "/check_templates/{check_template_id}"
)
NEW_CHECK_PATH: Final[str] = ROUTE_PREFIX + "/checks/"
GET_CHECK_PATH: Final[str] = ROUTE_PREFIX + "/checks/{check_id}"
UPDATE_CHECK_PATH: Final[str] = ROUTE_PREFIX + "/checks/{check_id}"
REMOVE_CHECK_PATH: Final[str] = ROUTE_PREFIX + "/checks/{check_id}"
LIST_CHECKS_PATH: Final[str] = ROUTE_PREFIX + "/checks/"


def get_exception(status_code: int, content: dict[str, Any]) -> CheckException:
    error_code = content[ERROR_CODE_KEY]
    message = content[ERROR_MESSAGE_KEY]
    match error_code:
        case CheckInternalError.__name__:
            return CheckInternalError(message)
        case CheckTemplateIdError.__name__:
            return CheckTemplateIdError(message)
        case CheckIdError.__name__:
            return CheckIdError(message)
        case CheckIdNonUniqueError.__name__:
            return CheckIdNonUniqueError(message)
        case CheckConnectionError.__name__:
            return CheckConnectionError(message)
        case _:
            return CheckInternalError(f"{error_code}: {message}")


# Can't accept dict[str, str] for query params because the same key might have multiple values.
def get_url_str(
    base_url: str,
    path: str,
    path_params: dict[str, str] | None = None,
    query_params_list: list[tuple[str, str]] | None = None,
) -> str:
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    path_str = (
        path.format_map(
            {
                parse.quote(key, safe=""): parse.quote(value, safe="")
                for key, value in path_params.items()
            }
        )
        if path_params
        else path
    )
    query_str = "?" + parse.urlencode(query_params_list) if query_params_list else ""
    return base_url + path_str + query_str
