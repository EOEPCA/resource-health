from enum import Enum
import json
from pathlib import Path
from typer import Argument, Context, Exit, Option, Typer
from typing import Optional
from typing_extensions import Annotated

__config_version__: str = "2.0.0"


class ServiceName(str, Enum):
    rest = "Remote"
    k8s = "Cluster"
    mock = "Mock"


config_app = Typer(no_args_is_help=True)
service_app = Typer(no_args_is_help=True)
config_app.add_typer(service_app, name="service")


@config_app.callback()
def config_callback():
    """
    Manage your configuration.
    """
    if not Path(".check").is_dir() and not Path(".check/config.json").is_file():
        print("Current directory not initialized.")
        raise Exit()


@service_app.callback()
def service_callback():
    """
    Manage which services to use for running health checks.
    """
    pass


def make_default_config() -> dict:
    return {
        "version": __config_version__,
        "authentication object": None,
        "services": [],
    }


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
    auth_obj: Annotated[Optional[str], Option()] = None,
) -> None:
    """
    Set chosen values in your configuration.
    """
    config_file: Path = Path(".check/config.json")
    config_dict: dict = {}
    with open(config_file, "r") as c:
        config_dict = json.load(c)
    with open(config_file, "w") as c:
        if auth_obj is not None:
            config_dict["authentication object"] = auth_obj
            print(f"Authentication object: {auth_obj}")
        json.dump(config_dict, c)


@config_app.command("get")
def get_config_value(
    auth_obj: Annotated[bool, Option("--auth-obj")] = False,
) -> None:
    """
    Print chosen values from your configuration.
    """
    config_file: Path = Path(".check/config.json")
    with open(config_file, "r") as c:
        config_dict = json.load(c)
        if auth_obj:
            print(f"Authentication object: {config_dict['authentication object']}")


def print_service(service: dict, index: int) -> None:
    print(f"{index}: {service['name']}")
    print(f"   with arguments \"{service['arg']}\"")


@service_app.command("add")
def add_service(
    service_name: Annotated[ServiceName, Argument(case_sensitive=False)],
    argument: Annotated[str, Argument()],
) -> None:
    """
    Add service to your configuration.
    """
    config_file: Path = Path(".check/config.json")
    config_dict: dict = {}
    with open(config_file, "r") as c:
        config_dict = json.load(c)
    service = {
        "name": service_name.value,
        "arg": argument,
    }
    config_dict["services"].append(service)
    print("Added service")
    print_service(service, len(config_dict["services"]))
    with open(config_file, "w") as c:
        json.dump(config_dict, c)


@service_app.command("remove")
def remove_service(
    index: Annotated[int, Argument()],
) -> None:
    """
    Remove service from configuration by list index.
    """
    config_file: Path = Path(".check/config.json")
    config_dict: dict = {}
    with open(config_file, "r") as c:
        config_dict = json.load(c)
    service = config_dict["services"][index - 1]
    print("Removed service")
    print_service(service, index)
    del config_dict["services"][index - 1]
    with open(config_file, "w") as c:
        json.dump(config_dict, c)


@service_app.command("list")
def list_services() -> None:
    """
    List configured services.
    """
    config_file: Path = Path(".check/config.json")
    with open(config_file, "r") as c:
        config_dict = json.load(c)
        for index, service in enumerate(config_dict["services"]):
            print_service(service, index + 1)
