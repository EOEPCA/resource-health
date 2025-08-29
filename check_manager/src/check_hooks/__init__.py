from functools import cache
from inspect import isfunction
import inspect
import logging
import pathlib
from typing import Any, Awaitable, Callable
import os

# from pydantic import Field
# from pydantic_settings import (
#     BaseSettings,
#     PydanticBaseSettingsSource,
#     SettingsConfigDict,
#     JsonConfigSettingsSource,
# )

from plugin_utils.loader import load_plugins
from api_utils.exceptions import APIForbiddenError
from check_backends.check_backend import CheckIdError, CheckTemplateIdError

logger = logging.getLogger("HEALTH_CHECK")


# class Settings(BaseSettings):
#     auth_hooks: Optional[str] = Field(
#         None, validation_alias="authentication_hooks"
#     )

#     model_config = SettingsConfigDict(
#         extra="ignore", json_file="authentication/config.json"
#     )

#     @classmethod
#     def settings_customise_sources(
#         cls,
#         settings_cls: Type[BaseSettings],
#         init_settings: PydanticBaseSettingsSource,
#         env_settings: PydanticBaseSettingsSource,
#         dotenv_settings: PydanticBaseSettingsSource,
#         file_secret_settings: PydanticBaseSettingsSource,
#     ) -> Tuple[PydanticBaseSettingsSource, ...]:
#         return (env_settings, JsonConfigSettingsSource(settings_cls),)

async def call_hooks_until_not_none(funcs: list[Callable], *args, **kwargs) -> Any:
    """
    Calls functions one by one until a function returns a result that is not None, in which case that result is returned.
    """
    for func in funcs:
        result = await _wait_if_async(func(*args, **kwargs))
        if result is not None:
            return result
    return None


async def call_hooks_ignore_results(funcs: list[Callable], *args, **kwargs) -> None:
    """
    Calls functions one by one and ignores the returned values
    """
    for func in funcs:
        await _wait_if_async(func(*args, **kwargs))


async def call_hooks_check_if_allow(funcs: list[Callable], *args, **kwargs) -> bool:
    """
    Calls functions one by one and if catch APIForbiddenError or CheckTemplateIdError or CheckIdError, return that it's not allowed (false)
    All other exceptions are not caught
    """
    for func in funcs:
        try:
            await _wait_if_async(func(*args, **kwargs))
        except (APIForbiddenError, CheckTemplateIdError, CheckIdError):
            return False
    return True


async def _wait_if_async[T](x: T | Awaitable[T]) -> T:
    if inspect.isawaitable(x):
        return await x

    return x


def _convert_file_based_hooks_to_name_based_hooks(
    file_to_hooks: dict[str, dict[str, Callable]],
) -> dict[str, list[Callable]]:
    file_names: list[str] = sorted(file_to_hooks.keys())
    hooks_by_files: list[dict[str, Callable]] = [
        file_to_hooks[name] for name in file_names
    ]
    hook_names = [
        hook_name for file_hooks in hooks_by_files for hook_name in file_hooks.keys()
    ]
    return {
        hook_name: [
            file_hooks[hook_name]
            for file_hooks in hooks_by_files
            if hook_name in file_hooks
        ]
        for hook_name in hook_names
    }


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
    return _convert_file_based_hooks_to_name_based_hooks(file_to_hooks)


# @cache
# def load_authentication(path: pathlib.Path):
# # def load_authentication(name, dirs: str | list[str]):
#     # print("load_authentication")
#     path = path.resolve()
#     hooks = load_functions(str(path.parent))[path.name.removesuffix('.py')]

#     authentication = {}

#     authentication["on_auth"] = (
#         hooks.get("on_auth") or
#         (lambda token: token)
#     )

#     authentication["get_check_templates_configuration"] = (
#         hooks.get("get_check_templates_configuration") or
#         hooks.get("default_configuration")
#     )

#     authentication["create_check_configuration"] = (
#         hooks.get("create_check_configuration") or
#         hooks.get("default_configuration")
#     )

#     authentication["remove_check_configuration"] = (
#         hooks.get("remove_check_configuration") or
#         hooks.get("default_configuration")
#     )

#     authentication["run_check_configuration"] = (
#         hooks.get("run_check_configuration") or
#         hooks.get("default_configuration")
#     )

#     authentication["get_checks_configuration"] = (
#         hooks.get("get_checks_configuration") or
#         hooks.get("default_configuration")
#     )

#     if not all([
#         authentication["get_check_templates_configuration"],
#         authentication["create_check_configuration"],
#         authentication["remove_check_configuration"],
#         authentication["run_check_configuration"],
#         authentication["get_checks_configuration"],
#     ]):
#         ValueError("Authentication underspecified")

#     authentication["get_namespace"] = hooks["get_namespace"]
#     authentication["get_userinfo"] = hooks["get_userinfo"]
#     authentication["template_access"] = hooks["template_access"]
#     authentication["cronjob_access"] = hooks["cronjob_access"]
#     authentication["tag_cronjob"] = hooks["tag_cronjob"]

#     return authentication
