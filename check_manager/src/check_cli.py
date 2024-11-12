import asyncio
from k8s_backend import K8sBackend
from lib import (
    AuthenticationObject,
    Check,
    CheckId,
    CheckBackend,
    CheckTemplateId,
    CronExpression,
)
from typer import Option, Typer
from typing_extensions import Annotated

check_backend: CheckBackend = K8sBackend()

app = Typer()


async def print_checks(auth_obj: AuthenticationObject) -> None:
    async for check in check_backend.list_checks(auth_obj):
        print(f"-Check id: {check.id}")
        print(f" Schedule: {check.schedule}")


@app.command("list")
def ls(auth_obj: Annotated[str, Option()] = "default_user"):
    asyncio.run(print_checks(AuthenticationObject(auth_obj)))


@app.command()
def create(
    auth_obj: Annotated[str, Option()],
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
    auth_obj: Annotated[str, Option()],
):
    asyncio.run(
        check_backend.remove_check(
            auth_obj=auth_obj,
            check_id=CheckId(id),
        )
    )
    print(f"Deleted check with id:{id}")


if __name__ == "__main__":
    app()
