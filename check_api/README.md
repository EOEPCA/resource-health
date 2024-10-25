# Check API

## Setup

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Install the required Python by running `uv python install`

## Usage

Run

```bash
uv run fastapi dev main.py
```

Upon executing the above, the openapi spec is written to `openapi.json`, and the api is launched.

Then go to http://127.0.0.1:8000/docs to see the API docs and experiment with the API
