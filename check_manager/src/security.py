from functools import cache
from inspect import isfunction
import logging
import pathlib
from typing import Any, Callable, Optional, Tuple, Type

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    JsonConfigSettingsSource,
)

from plugin_utils.loader import load_plugins

logger = logging.getLogger("HEALTH_CHECK")


class Settings(BaseSettings):
    auth_hooks: Optional[str] = Field(
        None, validation_alias="authentication_hooks"
    )

    model_config = SettingsConfigDict(
        extra="ignore", json_file="authentication/config.json"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (env_settings, JsonConfigSettingsSource(settings_cls),)


def load_functions(dirs: str | list[str]) -> dict[str, Callable]:
    paths: list[str] = dirs if isinstance(dirs, list) else [dirs]
    hooks: dict[str, Any] = {}
    for path in paths:
        hooks.update(
            load_plugins(
                pathlib.Path(path),
                value=(lambda x: x if isfunction(x) else None),
                logger=logger,
                perfile=True,
            )
        )
    return hooks


@cache
def load_authentication(path: pathlib.Path):
# def load_authentication(name, dirs: str | list[str]):
    # print("load_authentication")
    path = path.resolve()
    hooks = load_functions(path.parent)[path.name.removesuffix('.py')]

    authentication = {}

    authentication["on_auth"] = (
        hooks.get("on_auth") or
        (lambda token: token)
    )

    authentication["get_check_templates_configuration"] = (
        hooks.get("get_check_templates_configuration") or
        hooks.get("default_configuration")
    )

    authentication["create_check_configuration"] = (
        hooks.get("create_check_configuration") or
        hooks.get("default_configuration")
    )

    authentication["remove_check_configuration"] = (
        hooks.get("remove_check_configuration") or
        hooks.get("default_configuration")
    )

    authentication["run_check_configuration"] = (
        hooks.get("run_check_configuration") or
        hooks.get("default_configuration")
    )

    authentication["get_checks_configuration"] = (
        hooks.get("get_checks_configuration") or
        hooks.get("default_configuration")
    )

    if not all([
        authentication["get_check_templates_configuration"],
        authentication["create_check_configuration"],
        authentication["remove_check_configuration"],
        authentication["run_check_configuration"],
        authentication["get_checks_configuration"],
    ]):
        ValueError("Authentication underspecified")

    authentication["get_namespace"] = hooks["get_namespace"]
    authentication["get_userinfo"] = hooks["get_userinfo"]
    authentication["template_access"] = hooks["template_access"]
    authentication["cronjob_access"] = hooks["cronjob_access"]
    authentication["tag_cronjob"] = hooks["tag_cronjob"]

    return authentication
