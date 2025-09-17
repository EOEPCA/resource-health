import inspect
from typing import Any, Awaitable, Callable


async def call_hooks_until_not_none(funcs: list[Callable], *args: Any, **kwargs: Any) -> Any:
    """
    Calls functions one by one until a function returns a result that is not None, in which case that result is returned.
    """
    for func in funcs:
        result = await wait_if_async(func(*args, **kwargs))
        if result is not None:
            return result
    return None


async def call_hooks_ignore_results(funcs: list[Callable], *args: Any, **kwargs: Any) -> None:
    """
    Calls functions one by one and ignores the returned values
    """
    for func in funcs:
        await wait_if_async(func(*args, **kwargs))

async def call_hooks_check_if_allow(exceptions: type[BaseException] | tuple[type[BaseException], ...], funcs: list[Callable], *args: Any, **kwargs: Any) -> bool:
    """
    Calls functions one by one and if catch any exception from exceptions, return that it's not allowed (false)
    All other exceptions are not caught
    """
    for func in funcs:
        try:
            await wait_if_async(func(*args, **kwargs))
        except exceptions:
            return False
    return True


async def wait_if_async[T](x: Awaitable[T] | T) -> T:
    return (await x) if inspect.isawaitable(x) else x