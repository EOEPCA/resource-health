import importlib.util
import importlib.machinery
import inspect
import logging
import pathlib
from types import ModuleType
from typing import Any, Callable


def load_python_module(path: pathlib.Path) -> ModuleType | None:
    """
    Load a Python module from a given file path.

    Args:
        path (pathlib.Path): The path to the Python file to be loaded.

    Returns:
       ModuleType | None: The loaded Python module, or `None` if the
        file is not a Python file.

    Raises:
        ImportError: If the module spec cannot be created or executed.
    """

    if path.suffix != '.py' or path.name == '__init__.py':
        return None

    module_name: str = path.stem
    spec: importlib.machinery.ModuleSpec | None = (
        importlib.util.spec_from_file_location(module_name, path)
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load spec for module: {module_name}")

    module: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_and_transform(
    items: list[tuple[str, Any]],
    key: Callable[[Any], str] | None = None,
    value: Callable[[Any], Any] | None = None,
) -> dict[str, Any]:
    """
    Extract and transform members from a list of (name, member) tuples.

    This function processes a list of member tuples and optionally applies
    transformation functions to the member names and values. If `key` and
    `value` functions are provided, they are used to modify the name and value
    of each member before adding it to the resulting dictionary.

    Args:
        items (list[tuple[str, Any]]): A list of tuples, each containing a
            member name and its associated object.
        key (Callable[[Any], str], optional): A function that transforms the
            member name. If not provided, the original member name is used.
        value (Callable[[Any], Any], optional): A function that transforms the
            member value. If not provided, the original member value is used.

    Returns:
        dict: A dictionary where the keys are the member names (transformed by
        `key` if provided), and the values are the members (transformed by
        `value` if provided).
    """
    members: dict[str, Any] = {}
    for name, member in items:
        obj: Any | None = value(member) if value else member
        if obj is not None:
            members[key(member) if key else name] = obj
    return members


def load_plugins(
    dir: pathlib.Path,
    perfile: bool = False,
    loader: Callable[[pathlib.Path], dict[str, Any] | None] | None = None,
    key: Callable[[Any], str] | None = None,
    value: Callable[[Any], Any] | None = None,
    logger: logging.Logger = logging.getLogger(__name__),
) -> dict[str, Any]:
    """
    Load and extract desired members from files in a directory.

    This function iterates through files in a directory and either loads Python
    modules or allows for custom loaders to handle non-Python files. After
    loading, it extracts members (objects) from each file and optionally
    transforms the keys (names) and values of these members.

    Args:
        dir (str): The directory path where files are located.
        perfile (bool, optional): If `True`, each file's members are stored
            under the file's name. If `False`, all members are combined into a
            single dictionary. Is set to `False` by default.
        loader (Callable[[pathlib.Path], dict | None], optional): A custom
            loader function that can load files other than Python files (e.g.,
            YAML, JSON). If not provided, the deafult `load_python_module`
            will be used, loading only Python files.
        key (Callable[[Any], str], optional): A function that transforms the
            name of each member. If not provided, the original name is used.
            This option is for if you want to use the default loader but want
            different keys different from the default names.
        value (Callable[[Any], Any], optional): A function that transforms the
            value of each member. If not provided, the original value is used.
        logger (logging.Logger, optional): A logger to report errors and
            information.  Defaults to a logger named after the module
            (`__name__`).

    Returns:
        dict: A dictionary containing the extracted members. If `perfile` is
        `True`, the dictionary keys are the file names, with each value being
        a dictionary of members extracted from that file. If `perfile` is
        `False`, all members are combined in a  single dictionary.

    Raises:
        ImportError: If loading a Python module fails.
        AttributeError: If extracting members from a file fails.
        Exception: For any other unexpected errors.
    """
    plugins: dict[str, Any] = {}

    if not dir.is_dir():
        logger.error(f"Provided path is not a directory: {dir}")
        return plugins

    for file in dir.iterdir():
        try:
            content: dict[str, Any] | ModuleType | None = (
                loader(file) if loader else
                load_python_module(file)
            )
            if content is not None:
                items: list[tuple[str, Any]] = (
                    list(content.items()) if content is dict else
                    inspect.getmembers(content)
                )
                members = extract_and_transform(items, key, value)
                plugins.update({file.stem: members} if perfile else members)
        except ImportError as e:
            logger.error(f"Module loading error for {file}: {str(e)}")
        except SyntaxError as e:
            logger.error(f"Syntax error when loading {file}: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error while processing {file}: {e}")

    return plugins
