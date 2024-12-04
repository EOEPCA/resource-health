from abc import ABC
# from jsonschema.exceptions import ValidationError


class CheckException(ABC, Exception):
    """Base exception class"""


class CheckInternalError(CheckException):
    """Check Id not found"""


class CheckTemplateIdError(CheckException, KeyError):
    """Template Id not found"""


class CheckIdError(CheckException, KeyError):
    """Check Id not found"""


class CheckIdNonUniqueError(CheckException, KeyError):
    """Check Id not unique"""


class CheckConnectionError(CheckException, ConnectionError):
    """HTTP request failed"""
