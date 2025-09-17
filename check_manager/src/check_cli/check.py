import asyncio
from base64 import b64encode
import importlib
import json
from pathlib import Path
from typer import Argument, Context, Exit, Option, Typer
from typing import Optional
from typing_extensions import Annotated

from eoepca_api_utils.exceptions import APIException
from check_backends.check_backend import (
    AggregationBackend,
    AuthenticationObject,
    CheckBackend,
    CheckId,
    CheckIdError,
    CheckTemplateId,
    CronExpression,
    InCheckAttributes,
    InCheckMetadata,
)
from check_backends.k8s_backend import K8sBackend
from check_backends.mock_backend import MockBackend
from check_backends.rest_backend import RestBackend
from exceptions import CheckConnectionError
from check_cli.check_config import config_app, make_default_config, ServiceName


app = Typer(no_args_is_help=True)
app.add_typer(config_app, name="config")
list_app = Typer(no_args_is_help=True)
app.add_typer(list_app, name="list")


def version_callback(value: bool):
    if value:
        print("check-manager version " + importlib.metadata.version("check-manager"))
        raise Exit()


@app.callback()
def common(
    ctx: Context,
    version: bool = Option(
        None,
        "--version",
        help="Print version information.",
        callback=version_callback,
    ),
):
    """
    Command line tool for managing and deploying resource-health checks.

    Find more information at https://github.com/EOEPCA/resource-health/tree/main
    """
    pass


@list_app.callback()
def list_callback():
    """
    List resources (templates or checks)
    """
    pass


def load_config() -> dict:
    config_dir: Path = Path(".check")
    config_file: Path = config_dir / "config.json"

    config_dict: Optional[dict] = None
    if config_dir.is_dir() and config_file.is_file():
        c = open(config_file, "r")
        config_dict = json.load(c)

    if config_dict:
        return config_dict
    else:
        print("Could not find configuration. Has this directory been initialized?")
        raise Exit()


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


def load_backend() -> AggregationBackend:
    services_list: list[dict] = []
    conf = load_config()
    if conf is not None:
        services_list = conf.get("services", [])

    services: list[CheckBackend] = []

    for service in services_list:
        match service["name"]:
            case ServiceName.k8s.value:
                services.append(K8sBackend(service["arg"]))
            case ServiceName.rest.value:
                services.append(RestBackend(service["arg"]))
            case ServiceName.mock.value:
                services.append(MockBackend(service["arg"]))

    if len(services) == 0:
        print("Make sure your services are correctly configured.")
        raise Exit()

    backend = AggregationBackend(services)

    return backend


class ExceptionHandler:
    """Async iterator wrapper to handle exceptions during iteration"""

    def __init__(self, iter):
        self.iter = iter

    def __aiter__(self):
        return self

    async def __anext__(self):
        while True:
            try:
                return await anext(self.iter)
            except StopAsyncIteration as stop:
                raise stop
            except CheckConnectionError as e:
                print(
                    f"Encountered an error when trying to connect to service: {str(e)}"
                )
                continue


async def print_templates(ids: Optional[list[CheckTemplateId]] = None) -> None:
    check_backend = load_backend()
    template_list = ExceptionHandler(check_backend.get_check_templates(ids))
    async for template in template_list:
        print(f"- Template id: {template.id}")
        print(f"  Label: {template.attributes.metadata.label}")
        print(f"  Description: {template.attributes.metadata.description}")
        if ids is not None:
            ids.remove(template.id)
    if ids is not None and len(ids) > 0:
        for i in ids:
            print(f"Could not find template with id: {i}")


async def print_checks(auth_obj: AuthenticationObject) -> None:
    check_backend = load_backend()
    check_list = ExceptionHandler(check_backend.get_checks(auth_obj))
    async for check in check_list:
        print(f"- Check id: {check.id}")
        print(f"  Schedule: {check.attributes.schedule}")


@list_app.command("templates")
def list_templates(ids: Annotated[Optional[list[str]], Argument()] = None):
    """
    List available templates.
    """
    if ids:
        asyncio.run(print_templates([CheckTemplateId(i) for i in ids]))
    else:
        asyncio.run(print_templates())


@list_app.command("checks")
def list_checks(auth_obj: Annotated[str, Option()] = "default_obj"):
    """
    List currently deployed health checks.
    """
    asyncio.run(print_checks(AuthenticationObject(auth_obj)))


def get_auth_obj() -> str:
    if not Path(".check").is_dir() and not Path(".check/config.json").is_file():
        print("No preset configuration. Give authentication object with '--auth-obj'.")
        raise Exit()
    config_file: Path = Path(".check/config.json")
    with open(config_file, "r") as c:
        config_dict = json.load(c)
        auth_obj: str | None = config_dict["authentication object"]
        if auth_obj is None:
            print(
                "No preset value for authentication object in configuration. Set value with '--auth-obj'."
            )
            raise Exit()
    return auth_obj


def if_only_one_service() -> int:
    conf: dict = load_config()
    if len(conf["services"]) > 1:
        print("More than one service configured. Choose which one to use.")
        raise Exit()
    return 1


def b64encode_file(file_name: str) -> str:
    if not Path(file_name).is_file():
        print(f"Could not find file: {file_name}")
        raise Exit()
    with open(file_name, "r") as f:
        return b64encode(f.read().encode("ascii")).decode("ascii")


@app.command("create")
def create_check(
    auth_obj: Annotated[str, Option(default_factory=get_auth_obj)],
    service_nr: Annotated[int, Option(default_factory=if_only_one_service)],
    template_id: Annotated[str, Option()],
    schedule: Annotated[str, Option()],
    health_check_name: Annotated[str, Option()],
    health_check_description: Annotated[str, Option()],
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

    # For AggregateBackend. Will be deleted after use.
    template_args.update({"service_index": service_nr - 1})

    check_backend = load_backend()

    try:
        check = asyncio.run(
            check_backend.create_check(
                auth_obj=AuthenticationObject(auth_obj),
                attributes=InCheckAttributes(
                    metadata=InCheckMetadata(
                        name=health_check_name,
                        description=health_check_description,
                        template_id=CheckTemplateId(template_id),
                        template_args=template_args,
                    ),
                    schedule=CronExpression(schedule),
                ),
            )
        )
    except CheckConnectionError as e:
        print(f"Encountered an error when trying to connect to service: {str(e)}")
        raise Exit()
    except APIException as e:
        print(f"Error: {e}")
        raise Exit()

    print("Created health check")
    print(f"- Check id: {check.id}")
    print(f"  Schedule: {check.attributes.schedule}")


@app.command("delete")
def delete_check(
    id: str,
    auth_obj: Annotated[str, Option(default_factory=get_auth_obj)],
):
    """
    Delete a deployed health check.
    """
    check_backend = load_backend()
    try:
        asyncio.run(
            check_backend.remove_check(
                auth_obj=AuthenticationObject(auth_obj),
                check_id=CheckId(id),
            )
        )
        print(f"Deleted check with id:{id}")
    except CheckIdError:
        print(f"No check with id:{id}")
        raise Exit()
    except CheckConnectionError as e:
        print(f"Encountered an error when trying to connect to service: {str(e)}")
        raise Exit()
    except APIException as e:
        print(f"Error: {e}")
        raise Exit()
