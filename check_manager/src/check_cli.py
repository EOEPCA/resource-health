import asyncio
from base64 import b64encode
import json
from k8s_backend import K8sBackend
from lib import (
    AggregationBackend,
    AuthenticationObject,
    Check,
    CheckId,
    CheckBackend,
    CheckTemplateId,
    CronExpression,
    MockBackend,
    RestBackend,
)
from pathlib import Path
from typer import Context, Exit, Option, Typer
from typing import Optional
from typing_extensions import Annotated

__version__: str = "0.0.1"

# check_backend: CheckBackend = K8sBackend()

app = Typer(no_args_is_help=True)
config_app = Typer(no_args_is_help=True)
app.add_typer(config_app, name="config")
list_app = Typer(no_args_is_help=True)
app.add_typer(list_app, name="list")


def version_callback(value: bool):
    if value:
        print(f"check version {__version__}")
        raise Exit()


@app.callback()
def common(
    ctx: Context,
    version: bool = Option(
        None,
        "--version",
        "-v",
        help="Print version information.",
        callback=version_callback,
    ),
):
    """
    Command line tool for managing and deploying resource-health checks.

    Find more information at https://github.com/EOEPCA/resource-health/tree/main
    """
    pass


@config_app.callback()
def config_callback():
    """
    Manage your configuration.
    """
    if not Path(".check").is_dir() and not Path(".check/config.json").is_file():
        print("Current directory not initialized.")
        raise Exit()


@list_app.callback()
def list_callback():
    """
    List resources (templates or checks)
    """
    pass


def make_default_config() -> dict:
    return {
        "version": __version__,
        "user": None,
        "backends": [],
    }


def load_config() -> Optional[dict]:
    config_dir: Path = Path(".check")
    config_file: Path = config_dir / "config.json"

    config_dict: Optional[dict] = None
    if config_dir.is_dir() and config_file.is_file():
        c = open(config_file, "r")
        config_dict = json.load(c)

    return config_dict


@app.command("init")
def init_config() -> None:
    """
    Create a local configuration in this directory.
    """
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
    """
    Reset the current configuration to the default.
    """
    config_file: Path = Path(".check/config.json")
    with open(config_file, "w") as c:
        json.dump(make_default_config(), c)


@config_app.command("purge")
def purge_config() -> None:
    """
    Remove configuration from the current directory.
    """
    from shutil import rmtree

    rmtree(".check")


@config_app.command("set")
def set_config_value(
    user_name: Annotated[Optional[str], Option()] = None,
    backend: Annotated[Optional[str], Option()] = None,
) -> None:
    """
    Set chosen values in your configuration.
    """
    config_file: Path = Path(".check/config.json")
    config_dict: dict = {}
    with open(config_file, "r") as c:
        config_dict = json.load(c)
    with open(config_file, "w") as c:
        if user_name is not None:
            config_dict["user"] = user_name
            print(f"User name: {user_name}")
        if backend is not None:
            if backend not in config_dict["backends"]:
                config_dict["backends"].append(backend)
            print(f"Backend: {backend}")
        json.dump(config_dict, c)


@config_app.command("get")
def get_config_value(
    user_name: Annotated[bool, Option("--user-name")] = False,
    backends: Annotated[bool, Option("--backends")] = False,
) -> None:
    """
    Print chosen values from your configuration.
    """
    config_file: Path = Path(".check/config.json")
    with open(config_file, "r") as c:
        config_dict = json.load(c)
        if user_name:
            print(f"User name: {config_dict['user']}")
        if backends:
            print(f"Backends: {config_dict['backends']}")


def load_backend() -> CheckBackend | AggregationBackend:
    backends_list: list[str] = []
    conf = load_config()
    if conf is not None:
        backends_list = conf.get("backends", [])

    backends: list[CheckBackend] = []

    if "k8sbackend" in backends_list:
        backends.append(K8sBackend())
    if "restbackend" in backends_list:
        backends.append(RestBackend("http://127.0.0.1:8000"))
    if "mockbackend" in backends_list:
        backends.append(MockBackend("local_"))

    if len(backends) == 0:
        print("Backends must be configured before using this command.")
        raise Exit()

    backend: CheckBackend | AggregationBackend
    if len(backends) > 1:
        backend = AggregationBackend(backends)
    else:
        backend = backends[0]

    return backend


async def print_templates() -> None:
    check_backend = load_backend()
    async for template in check_backend.list_check_templates():
        print(f"- Template id: {template.id}")
        print(f"  Label: {template.metadata['label']}")
        print(f"  Description: {template.metadata['description']}")


async def print_checks(auth_obj: AuthenticationObject) -> None:
    check_backend = load_backend()
    async for check in check_backend.list_checks(auth_obj):
        print(f"- Check id: {check.id}")
        print(f"  Schedule: {check.schedule}")


@list_app.command("templates")
def list_templates():
    """
    List available templates.
    """
    asyncio.run(print_templates())


@list_app.command("checks")
def list_checks(auth_obj: Annotated[str, Option()] = "default_user"):
    """
    List currently deployed health checks.
    """
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
            print(
                "No preset value for user name in configuration. Give user name with '--user-name'."
            )
            raise Exit()
    return user_name


def b64encode_file(file_name: str) -> str:
    if not Path(file_name).is_file():
        print(f"Could not find file: {file_name}")
        raise Exit()
    with open(file_name, "r") as f:
        return b64encode(f.read().encode("ascii")).decode("ascii")


@app.command("create")
def create_check(
    auth_obj: Annotated[str, Option(default_factory=get_user_name)],
    schedule: Annotated[str, Option()],
    template_id: Annotated[str, Option()] = CheckTemplateId("default_k8s_template"),
    url: Annotated[Optional[str], Option()] = None,
    file: Annotated[Optional[str], Option()] = None,
    url_req: Annotated[Optional[str], Option()] = None,
    file_req: Annotated[Optional[str], Option()] = None,
):
    """
    Create and deploy a new health check.
    """
    template_args: dict = {"script": None}
    if url is not None and file is not None:
        print("Use one of '--url' or '--file'.")
        raise Exit()
    if url is not None:
        template_args["script"] = url
    elif file is not None:
        template_args["script"] = f"data:text/plain;base64,{b64encode_file(file)}"
    else:
        print("Script is required. Use either '--url' or '--file'.")
        raise Exit()

    if url_req is not None and file_req is not None:
        print("Use one of '--url_req' or '--file_req'.")
        raise Exit()
    if url_req is not None:
        template_args.update({"requirements": "url_req"})
    elif file_req is not None:
        template_args.update(
            {"requirements": f"data:text/plain;base64,{b64encode_file(file_req)}"}
        )

    check_backend = load_backend()
    check: Check = asyncio.run(
        check_backend.new_check(
            auth_obj=AuthenticationObject(auth_obj),
            template_id=template_id,
            template_args=template_args,
            schedule=CronExpression(schedule),
        )
    )
    print(check)


@app.command("delete")
def delete_check(
    id: str,
    auth_obj: Annotated[str, Option(default_factory=get_user_name)],
):
    """
    Delete a deployed health check.
    """
    check_backend = load_backend()
    asyncio.run(
        check_backend.remove_check(
            auth_obj=AuthenticationObject(auth_obj),
            check_id=CheckId(id),
        )
    )
    print(f"Deleted check with id:{id}")


if __name__ == "__main__":
    app()
