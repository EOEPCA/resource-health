from check_api.hook_utils import *

from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import TypedDict
import os

class UserInfo(TypedDict):
    username : str

def get_fastapi_security() -> HTTPBasic:
    return HTTPBasic(
        auto_error=False
    )


def on_auth(auth_info: HTTPBasicCredentials | None) -> UserInfo:
    if auth_info is None:
        return UserInfo(username='unauthorized_user')
    else:
        return UserInfo(username=HTTPBasicCredentials.username)

## For the mock backend


def get_mock_username(userinfo: UserInfo) -> str:
    return userinfo["username"]
