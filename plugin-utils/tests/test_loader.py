import contextlib
import importlib.util
import inspect
import json
import pathlib
from types import ModuleType, NoneType
from typing import Any, Callable
from unittest.mock import MagicMock, Mock, patch

import pytest

from plugin_utils.loader import (
    load_python_module,
    extract_and_transform,
    load_plugins,
)


@pytest.mark.parametrize(
    (
        "file_name,"
        "content,"
        "expected,"
        "expectation"
    ),
    [
        (
            "python_module.py",
            "",
            ModuleType,
            contextlib.nullcontext(),
        ),
        (
            "not_a_python_module",
            "",
            NoneType,
            contextlib.nullcontext(),
        ),
        (
            "not_a_file.py",
            None,
            None,
            pytest.raises(FileNotFoundError),
        ),
        (
            "invalid_python.py",
            "!",
            None,
            pytest.raises(SyntaxError),
        ),
    ]
)
def test_load_python_module(
    tmp_path: pathlib.Path,
    file_name: str,
    content: str | None,
    expected: type | None,
    expectation: contextlib.AbstractContextManager,
) -> None:
    test_module = tmp_path / file_name
    if content is not None:
        with open(test_module, "w") as file:
            file.write(content)

    with expectation:
        mod = load_python_module(test_module)
        assert type(mod) is expected


@pytest.mark.parametrize("items, key, value, expected", [
    (
        [],
        None,
        None,
        {},
    ),
    (
        [("a", "a_value")],
        None,
        None,
        {"a": "a_value"},
    ),
    (
        [("a", "a_value"), ("b", "b_value")],
        None,
        None,
        {
            "a": "a_value",
            "b": "b_value",
        },
    ),
    (
        [("a", "a_value"), ("b", "b_value")],
        (lambda s: s[0:3].capitalize()),
        None,
        {
            "A_v": "a_value",
            "B_v": "b_value",
        },
    ),
    (
        [("a", "a_value"), ("b", "b_value")],
        None,
        (lambda v: v[0:3].capitalize()),
        {
            "a": "A_v",
            "b": "B_v",
        },
    ),
    (
        [("a", "a_value"), ("b", "b_value")],
        None,
        (lambda v: v if v[0] != "b" else None),
        {
            "a": "a_value",
        },
    ),
])
def test_extract_and_transform(
    items: list[tuple[str, Any]],
    key: Callable[[Any], str] | None,
    value: Callable[[Any], Any] | None,
    expected: dict[str, Any],
) -> None:
    members = extract_and_transform(
        items=items,
        key=key,
        value=value,
    )
    assert members == expected


def load_json(path: pathlib.Path) -> dict[str, Any] | None:
    res: dict[str, Any] | None = None
    if path.suffix == ".json":
        with open(path) as file:
            res = json.load(file)
    return res


def raise_exception() -> None:
    raise Exception()



@pytest.mark.parametrize(
    "perfile", ["True", "False"]
)
@pytest.mark.parametrize(
    (
        "content,"
        "suffix,"
        "loader,"
        "key,"
        "value,"
        "expected,"
        "log"
    ),
    [
        (
            "",
            ".py",
            None,
            None,
            (lambda x: x if inspect.isclass(x) else None),
            [],
            None,
        ),
        (
            "class A:\n  pass\n\n\ndef f():\n  pass",
            ".py",
            None,
            None,
            (lambda x: x if inspect.isclass(x) else None),
            ["A"],
            None,
        ),
        (
            "class A:\n  pass\n\n\ndef f():\n  pass",
            ".py",
            None,
            None,
            (lambda x: x if inspect.isfunction(x) else None),
            ["f"],
            None,
        ),
        (
            "class A:\n  pass\n\n\ndef f():\n  pass",
            ".py",
            None,
            None,
            (lambda x: x if inspect.ismodule(x) else None),
            [],
            None,
        ),
        (
            "{'A': 'B'}",
            ".json",
            None,
            load_json,
            None,
            ["A"],
            None,
        ),
        (
            "{'A': 'B', 'L': [1 2 3]}",
            ".json",
            None,
            load_json,
            None,
            ["A", "L"],
            None,
        ),
        (
            "clas A:\n  pass",
            ".py",
            None,
            None,
            None,
            [],
            "error",
        ),
        (
            "class A:\n  pass",
            ".py",
            None,
            None,
            raise_exception,
            [],
            "exception",
        ),
    ]
)
def test_load_plugins(
    tmp_path: pathlib.Path,
    content: str,
    suffix: str,
    loader: Callable[[pathlib.Path], dict | None] | None,
    key: Callable[[Any], str] | None,
    value: Callable[[Any], Any] | None,
    expected: list[str] | None,
    log: str | None,
    perfile: bool,
) -> None:
    file_name: str = "module"
    test_module: pathlib.Path = tmp_path / file_name
    if content is not None:
        with open(test_module.with_suffix(suffix), "w") as file:
            file.write(content)

    logger = MagicMock()

    plugins = load_plugins(
        dir=tmp_path,
        perfile=perfile,
        loader=loader,
        key=key,
        value=value,
        logger=logger,
    )

    match log:
        case None:
            logger.error.assert_not_called()
            logger.exception.assert_not_called()
        case "error":
            logger.error.assert_called_once()
            logger.exception.assert_not_called()
        case "exception":
            logger.error.assert_not_called()
            logger.exception.assert_called_once()
        case _:
            assert False

    if plugins == {}:
        return None

    if perfile:
        assert list(plugins[test_module.stem].keys()) == expected
    else:
        assert list(plugins.keys()) == expected


def test_not_a_directory() -> None:
    logger = MagicMock()
    dir = pathlib.Path("not/an/actual/path")
    plugins = load_plugins(
        dir=dir,
        logger=logger,
    )
    logger.error.assert_called_once_with(
        f"Provided path is not a directory: {dir}"
    )
    logger.exception.assert_not_called()


@patch("importlib.util.spec_from_file_location", return_value=None)
def test_empty_spec(
    mock_spec_from_file_location: Mock,
    tmp_path: pathlib.Path,
) -> None:
    logger = MagicMock()
    file_name: str = "module"
    test_module: pathlib.Path = tmp_path / file_name
    with open(test_module.with_suffix(".py"), "w") as file:
        file.write("")

    plugins = load_plugins(
        dir=tmp_path,
        logger=logger,
    )

    mock_spec_from_file_location.assert_called_once_with(
        file_name,
        test_module.with_suffix(".py"),
    )
    logger.error.assert_called_once()
    logger.exception.assert_not_called()
