# Plugin utils

A hopefully growing collection of utilities to make it easier to load and use plugins for your Python application or framework.

## Setup

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Run `uv sync` in the `plugin-utils` directory to install dependencies and build the project.

## Usage

Not available on PyPI yet but using `uv` you can add
```toml
[tool.uv.sources]
plugin_utils = { git = "https://github.com/EOEPCA/resource-helath/plugin-utils.git", branch = "deploy-develop" }
```
to your `pyproject.toml` to make it available as a dependency.

## Development

To run tests use `uv run pytest`. For type checking use `uv run mypy`. If adding more tests you can use `uv run mypy tests` to type check the tests.
