from fastapi import Request
import check_hooks.hook_utils as hu  # noqa: F401 might be used later

from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import TypedDict


class UserInfo(TypedDict):
    username: str


async def get_fastapi_security(request: Request) -> HTTPBasicCredentials | None:
    return await HTTPBasic(auto_error=False)(request)


def on_auth(auth_info: HTTPBasicCredentials | None) -> UserInfo:
    if auth_info is None:
        return UserInfo(username="unauthorized_user")
    else:
        return UserInfo(username=auth_info.username)


## For the mock backend


def get_mock_username(userinfo: UserInfo) -> str:
    return userinfo["username"]
