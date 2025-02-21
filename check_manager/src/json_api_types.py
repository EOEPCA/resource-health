from pydantic import BaseModel


class LinkObject(BaseModel):
    href: str
    # rel: str | None = None
    # describedby: str | None = None
    title: str | None = None
    # Double comment so that mypy doesn't think I'm trying to specify type using comment
    ## type: str | None = None
    # hreflang: str | None = None
    # meta: Json | None = None


type Link = str | LinkObject


# class Relationships(BaseModel):
#     links: dict[str, Link] | None = None
#     data: object | None = None
#     meta: object | None = None


class Links(BaseModel, extra="allow"):
    self: Link | None = None
    # related: object | None = None
    describedby: Link | None = None
    # first: Link | None = None
    # last: Link | None = None
    # prev: Link | None = None
    # next: Link | None = None
    root: Link | None = None


class Resource[T](BaseModel):
    id: str
    type: str
    attributes: T
    # relationships: object | None = None
    links: dict[str, Link] | None = None
    # meta: object | None = None


# class ResourceIdentifier(BaseModel):
#     id: str
# Double comment so that mypy doesn't think I'm trying to specify type using comment
##     type: str
#     meta: object | None = None


class Error(BaseModel):
    # id: str | None = None
    # links: dict[str, Link] | None = None
    # status: str | None = None
    code: str | None = None
    title: str | None = None
    detail: str | None = None
    # source: str | None = None
    meta: object | None = None


class APIOKResponse[T](BaseModel):
    data: Resource[T]
    # meta: Json | None = None
    # jsonapi: Json | None = None
    links: Links | None = None
    # included: list[Resource] | None = None


class APIOKResponseList[T](BaseModel):
    data: list[Resource[T]]
    # meta: Json | None = None
    # jsonapi: Json | None = None
    links: Links | None = None
    # included: list[Resource] | None = None


# class APIOKResponseNoData[T](BaseModel):
#     # meta: Json | None = None
#     # jsonapi: Json | None = None
#     links: Links | None = None
#     # included: list[Resource] | None = None


class APIErrorResponse(BaseModel):
    errors: list[Error] | None = None
    # meta: Json | None = None
    # jsonapi: Json | None = None
    # links: Links | None = None
