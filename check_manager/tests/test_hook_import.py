import contextlib
from dataclasses import dataclass
from typing import Any, Callable

import pytest
from api_utils.exceptions import APIException, APIForbiddenError
from check_backends.check_backend import (
    CheckId,
    CheckIdError,
    CheckTemplateId,
    CheckTemplateIdError,
)
from check_hooks import (
    _convert_file_based_hooks_to_name_based_hooks,
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
            raise APIForbiddenError(title="", detail="")
        case "b":
            raise CheckTemplateIdError(CheckTemplateId(""))
        case "c":
            raise CheckIdError(CheckId(""))
        case "d":
            raise APIException(status="", title="", detail="")


def hookD(a: str) -> Any:
    raise APIForbiddenError(title="", detail="")


@dataclass
class HooksExtractionArgs:
    file_to_hooks: dict[str, dict[str, Callable]]
    expected_name_to_hooks: dict[str, list[Callable]]


@pytest.mark.parametrize(
    ("args"),
    [
        HooksExtractionArgs(
            file_to_hooks={
                "fileA": {"funcA": hookA, "funcB": hookB},
                "fileB": {"funcB": hookC, "funcC": hookB},
                "fileC": {},
            },
            expected_name_to_hooks={
                "funcA": [hookA],
                "funcB": [hookB, hookC],
                "funcC": [hookB],
            },
        ),
        HooksExtractionArgs(
            file_to_hooks={
                "fileB": {"funcB": hookC, "funcC": hookB},
                "fileA": {"funcA": hookA, "funcB": hookB},
                "fileC": {},
            },
            expected_name_to_hooks={
                "funcA": [hookA],
                "funcB": [hookB, hookC],
                "funcC": [hookB],
            },
        ),
    ],
)
def test_hook_list_extraction(args: HooksExtractionArgs) -> None:
    assert (
        _convert_file_based_hooks_to_name_based_hooks(args.file_to_hooks)
        == args.expected_name_to_hooks
    )


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
            expectation=pytest.raises(APIForbiddenError),
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
            expectation=pytest.raises(APIForbiddenError),
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
            expectation=contextlib.nullcontext(False),
        ),
        HooksArgs(
            funcs=[hookA, hookB, hookC],
            args=["d"],
            kwargs={},
            expectation=pytest.raises(APIException),
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
            await call_hooks_check_if_allow(args.funcs, *args.args, **args.kwargs) == e
        )
