import asyncio
import json
from k8s_backend import K8sBackend
from lib import (
    AuthenticationObject,
    Check,
    CheckId,
    CheckBackend,
    CheckTemplateId,
    CronExpression,
)
from pathlib import Path
from typer import Context, Exit, Option, Typer
from typing import Optional
from typing_extensions import Annotated

__version__: str = "0.0.1"

check_backend: CheckBackend = K8sBackend()

app = Typer()
config_app = Typer()
app.add_typer(config_app, name="config")


def version_callback(value: bool):
    if value:
        print(f"check version {__version__}")
        raise Exit()


@app.callback()
def common(
    ctx: Context,
    version: bool = Option(None, "--version", "-v", callback=version_callback),
):
    pass


@config_app.callback()
def config_callback():
    if not Path(".check").is_dir() and not Path(".check/config.json").is_file():
        print("Current directory not initialized.")
        raise Exit()


def make_default_config() -> dict:
    return {
        "version": __version__,
        "user": None,
        "backend": None,
    }


@app.command("init")
def init_config() -> None:
    config_dir: Path = Path(".check")
    config_file: Path = config_dir / "config.json"

    if config_dir.is_dir() and config_file.is_file():
        print("Directory already initialized.")
        raise Exit()

    config_dir.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as c:
        json.dump(make_default_config(), c)


@config_app.command("reset")
def reset_config() -> None:
    config_file: Path = Path(".check/config.json")
    with open(config_file, "w") as c:
        json.dump(make_default_config(), c)


@config_app.command("purge")
def purge_config() -> None:
    from shutil import rmtree
    rmtree(".check")


@config_app.command("set")
def set_config_value(
    user_name: Annotated[Optional[str], Option()] = None,
    backend: Annotated[Optional[str], Option()] = None,
) -> None:
    config_file: Path = Path(".check/config.json")
    config_dict: dict = {}
    with open(config_file, "r") as c:
        config_dict = json.load(c)
    with open(config_file, "w") as c:
        if user_name is not None:
            config_dict["user"] = user_name
            print(f"User name: {user_name}")
        if backend is not None:
            config_dict["backend"] = backend
            print(f"Backend: {backend}")
        json.dump(config_dict, c)


@config_app.command("get")
def get_config_value(
    user_name: Annotated[bool, Option("--user-name")] = False,
    backend: Annotated[bool, Option("--backend")] = False,
) -> None:
    config_file: Path = Path(".check/config.json")
    with open(config_file, "r") as c:
        config_dict = json.load(c)
        if user_name:
            print(f"User name: {config_dict['user']}")
        if backend:
            print(f"Backend: {config_dict['backend']}")


async def print_checks(auth_obj: AuthenticationObject) -> None:
    async for check in check_backend.list_checks(auth_obj):
        print(f"-Check id: {check.id}")
        print(f" Schedule: {check.schedule}")


@app.command("list")
def ls(auth_obj: Annotated[str, Option()] = "default_user"):
    asyncio.run(print_checks(AuthenticationObject(auth_obj)))


def get_user_name() -> str:
    if not Path(".check").is_dir() and not Path(".check/config.json").is_file():
        print("No preset configuration. Give user name with '--user-name'.")
        raise Exit()
    config_file: Path = Path(".check/config.json")
    with open(config_file, "r") as c:
        config_dict = json.load(c)
        user_name = config_dict["user"]
        if user_name is None:
            print("No preset value for user name in configuration. Give user name with '--user-name'.")
            raise Exit()


@app.command()
def create(
    auth_obj: Annotated[str, Option(default_factory=get_user_name)],
    schedule: Annotated[str, Option()],
):
    # print("Create new check:")
    check: Check = asyncio.run(
        check_backend.new_check(
            auth_obj=AuthenticationObject(auth_obj),
            template_id=CheckTemplateId("Null"),
            template_args=dict(),
            schedule=CronExpression(schedule),
        )
    )
    print(check)


@app.command()
def delete(
    id: str,
    auth_obj: Annotated[str, Option(default_factory=get_user_name)],
):
    asyncio.run(
        check_backend.remove_check(
            auth_obj=AuthenticationObject(auth_obj),
            check_id=CheckId(id),
        )
    )
    print(f"Deleted check with id:{id}")


if __name__ == "__main__":
    app()
