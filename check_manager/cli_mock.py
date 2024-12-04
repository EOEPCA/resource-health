import asyncio
from lib import (
    AggregationBackend,
    CheckBackendContextManager,
    MockBackend,
    RestBackend,
    AuthenticationObject,
)


async def main():
    async with CheckBackendContextManager(
        AggregationBackend(
            [
                MockBackend(template_id_prefix="local_"),
                RestBackend("http://127.0.0.1:8000"),
            ]
        )
    ) as check_backend:
        auth_obj = AuthenticationObject("Jonas1")
        await check_backend.new_check(
            auth_obj,
            template_id="local_check_template1",
            template_args={},
            schedule="1:2:3",
        )
        check = await check_backend.new_check(
            auth_obj,
            template_id="remote_check_template1",
            template_args={},
            schedule="100",
        )
        print(check)
        print([_check async for _check in check_backend.list_checks(auth_obj, None)])
        await check_backend.update_check(
            auth_obj,
            check_id=check.id,
            template_id="check_template1",
            template_args={"new_arg": "some_value"},
        )
        print([_check async for _check in check_backend.list_checks(auth_obj, None)])
        await check_backend.remove_check(auth_obj, check.id)


asyncio.run(main())
