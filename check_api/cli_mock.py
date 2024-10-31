import asyncio
from lib import RestBackend, AuthenticationObject


async def main():
    async with RestBackend("http://127.0.0.1:8000") as check_backend:
        auth_obj = AuthenticationObject("Jonas1")
        check_id = await check_backend.new_check(
            auth_obj,
            template_id="check_template1",
            template_args={},
            schedule="1:2:3",
        )
        print(await check_backend.list_checks(auth_obj, None))
        await check_backend.update_check(
            auth_obj,
            check_id=check_id,
            template_id="check_template1",
            template_args={"new_arg": "some_value"},
        )
        print(await check_backend.list_checks(auth_obj, None))
        await check_backend.remove_check(auth_obj, check_id)


asyncio.run(main())
