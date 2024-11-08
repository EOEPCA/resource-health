import asyncio
from types import TracebackType
import httpx
import ijson
from typing import AsyncIterator, Literal, Self, Type


class HttpxStreamAsFile:
    def __init__(self, client: httpx.AsyncClient, request: httpx.Request):
        self._request = request
        self._data: AsyncIterator[bytes] | None = None
        self._client = client

    async def __aenter__(self: Self) -> Self:
        self._res = await self._client.send(self._request, stream=True)
        self._data = self._res.aiter_bytes()
        return self

    async def __aexit__(
        self: Self,
        exctype: Type[BaseException] | None,
        excinst: BaseException | None,
        exctb: TracebackType | None,
    ) -> Literal[False]:
        await self._res.aclose()
        return False

    async def read(self, n: int) -> bytes:
        if self._data is None or n == 0:
            return b""

        return await anext(self._data, b"")


async def main():
    url = "http://127.0.0.1:8000/dummy"
    async with httpx.AsyncClient() as client:
        async with HttpxStreamAsFile(
            client, client.build_request("GET", url)
        ) as httpx_as_file:
            async for obj in ijson.items(httpx_as_file, "item"):
                print(obj)


asyncio.run(main())
