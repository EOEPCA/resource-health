from functools import cache
from inspect import isfunction
import logging
import pathlib
from typing import Any, Callable
import os

import plugin_utils
from plugin_utils.loader import (
    load_plugins,
    convert_file_based_hooks_to_name_based_hooks,
)
from eoepca_api_utils.exceptions import APIForbiddenError
from check_backends.check_backend import CheckIdError, CheckTemplateIdError

logger = logging.getLogger("HEALTH_CHECK")


async def call_hooks_check_if_allow(
    funcs: list[Callable], *args: Any, **kwargs: Any
) -> bool:
    return await plugin_utils.runner.call_hooks_check_if_allow(
        (APIForbiddenError, CheckTemplateIdError, CheckIdError), funcs, *args, **kwargs
    )


@cache
def load_hooks(
    hooks_dir: pathlib.Path | str | None = None,
) -> dict[str, list[Callable]]:
    """
    Each hook might have multiple functions. The files with earlier alphanumeric names
    will have their hooks called earlier.
    """
    hooks_dir = hooks_dir or os.environ.get("RH_CHECK_HOOK_DIR_PATH")

    if hooks_dir is None:
        return {}

    file_to_hooks: dict[str, dict[str, Callable]] = load_plugins(
        pathlib.Path(hooks_dir),
        value=(lambda x: x if isfunction(x) else None),
        logger=logger,
        perfile=True,
    )
    return convert_file_based_hooks_to_name_based_hooks(file_to_hooks)
