import contextlib
from dataclasses import dataclass
from typing import Any, Callable

import pytest
from plugin_utils.runner import (
    call_hooks_check_if_allow,
    call_hooks_ignore_results,
    call_hooks_until_not_none,
)


def hookA(a: str) -> Any:
    return None


def hookB(a: str) -> Any:
    return a + "B"


async def hookC(a: str) -> Any:
    match a:
        case "a":
            raise ValueError("a")
        case "b":
            # inherits from RuntimeError
            raise NotImplementedError("b")
        case "c":
            raise RuntimeError("c")


@dataclass
class HooksArgs:
    funcs: list[Callable]
    args: list[Any]
    kwargs: dict[str, Any]
    expectation: contextlib.AbstractContextManager


@pytest.mark.parametrize(
    ("args"),
    [
        HooksArgs(
            funcs=[hookA],
            args=["a"],
            kwargs={},
            expectation=contextlib.nullcontext(None),
        ),
        HooksArgs(
            funcs=[hookA, hookB, hookC],
            args=["a"],
            kwargs={},
            expectation=contextlib.nullcontext("aB"),
        ),
        HooksArgs(
            funcs=[hookA, hookB, hookC],
            args=[],
            kwargs={"a": "a"},
            expectation=contextlib.nullcontext("aB"),
        ),
        HooksArgs(
            funcs=[hookA, hookC, hookB],
            args=["a"],
            kwargs={},
            expectation=pytest.raises(ValueError),
        ),
    ],
)
async def test_call_hooks_until_not_none(args: HooksArgs) -> None:
    with args.expectation as e:
        assert (
            await call_hooks_until_not_none(args.funcs, *args.args, **args.kwargs) == e
        )


@pytest.mark.parametrize(
    ("args"),
    [
        HooksArgs(
            funcs=[hookA, hookB, hookC],
            args=["a"],
            kwargs={},
            expectation=pytest.raises(ValueError),
        ),
        HooksArgs(
            funcs=[hookA, hookB],
            args=[],
            kwargs={"a": "a"},
            expectation=contextlib.nullcontext(),
        ),
    ],
)
async def test_call_hooks_ignore_results(args: HooksArgs) -> None:
    with args.expectation:
        assert (
            await call_hooks_ignore_results(args.funcs, *args.args, **args.kwargs)  # type: ignore
            is None
        )


@pytest.mark.parametrize(
    ("args"),
    [
        HooksArgs(
            funcs=[hookA, hookB, hookC],
            args=["a"],
            kwargs={},
            expectation=contextlib.nullcontext(False),
        ),
        HooksArgs(
            funcs=[hookA, hookB, hookC],
            args=["b"],
            kwargs={},
            expectation=contextlib.nullcontext(False),
        ),
        HooksArgs(
            funcs=[hookA, hookB, hookC],
            args=["c"],
            kwargs={},
            expectation=pytest.raises(RuntimeError),
        ),
        HooksArgs(
            funcs=[hookA, hookB, hookC],
            args=["bla"],
            kwargs={},
            expectation=contextlib.nullcontext(True),
        ),
        HooksArgs(
            funcs=[hookA, hookB],
            args=[],
            kwargs={"a": "hello"},
            expectation=contextlib.nullcontext(True),
        ),
    ],
)
async def test_call_hooks_check_if_allow(args: HooksArgs) -> None:
    with args.expectation as e:
        assert (
            await call_hooks_check_if_allow(
                (ValueError, NotImplementedError), args.funcs, *args.args, **args.kwargs
            )
            == e
        )
