from os import environ
from typing import Any
from fastapi import APIRouter, FastAPI, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from api_utils.json_api_types import APIErrorResponse


class JSONAPIResponse(JSONResponse):
    media_type = "application/vnd.api+json"


def get_api_router_with_defaults() -> APIRouter:
    return APIRouter(
        default_response_class=JSONAPIResponse,
        responses={status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": APIErrorResponse}},
    )


def get_env_var_or_throw(name: str) -> str:
    base_url = environ.get(name)
    if base_url is None:
        raise ValueError(f"Environment variable {name} must be set")
    return base_url


def set_custom_json_schema(app: FastAPI, title: str, version: str, **args) -> None:
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=title, version=version, routes=app.routes, **args
        )

        for _, path_schema in openapi_schema["paths"].items():
            for _, method_schema in path_schema.items():
                if "requestBody" in method_schema:
                    content: dict[str, Any] = method_schema["requestBody"]["content"]
                    content["application/vnd.api+json"] = content.pop(
                        "application/json"
                    )
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore
