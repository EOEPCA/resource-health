from typing import Final
from exceptions import (
    CheckException,
    CheckInternalError,
    CheckIdError,
    CheckIdNonUniqueError,
)

type Json = dict[str, object]


ERROR_CODE_KEY: Final[str] = "code"
ERROR_MESSAGE_KEY: Final[str] = "detail"


LIST_CHECK_TEMPLATES_PATH: Final[str] = "/check_templates/"
NEW_CHECK_PATH: Final[str] = "/checks/"
UPDATE_CHECK_PATH: Final[str] = "/checks/{check_id}"
REMOVE_CHECK_PATH: Final[str] = "/checks/{check_id}"
LIST_CHECKS_PATH: Final[str] = "/checks/"


def get_exception(status_code: int, content: Json) -> CheckException:
    error_code = content[ERROR_CODE_KEY]
    message: str = content[ERROR_MESSAGE_KEY]
    match error_code:
        case CheckInternalError.__name__:
            return CheckInternalError(message)
        case CheckIdError.__name__:
            return CheckIdError(message)
        case CheckIdNonUniqueError.__name__:
            return CheckIdNonUniqueError(message)
        case _:
            return CheckInternalError(f"{error_code}: {message}")
