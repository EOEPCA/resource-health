# Check manager

## Setup

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Either do a regular install with `uv pip install .` or install as an editable package with `uv pip install -e .`.

## Usage

### CLI

Run

```bash
uv run check --help
```

for instuctions how to use the CLI.

### API server

Run

```bash
RH_CHECK_API_BASE_URL=http://127.0.0.1:8000 uv run check-api-server-dev
```

Upon executing the above, the openapi spec is written to `openapi.json`, and the api is launched.

Then go to http://127.0.0.1:8000/docs to see the API docs and experiment with the API. This instance runs with the `MockBackend` and reloads any changes you make to the code.

If you want to launch the same server in production mode (or run this dummy server from Docker container), run

```bash
RH_CHECK_API_BASE_URL=http://127.0.0.1:8000 uv run check-api-server-dummy-prod
```


If you have running Kubernetes cluster you can run

```bash
RH_CHECK_API_BASE_URL=http://127.0.0.1:8000 uv run check-api-server-k8s
```

which uses the `K8sBackend` and does not reload unless you restart the server.

## Docker image

From the current directory build the image with

```bash
docker build -t check_manager -f Dockerfile .
```

Run the image with (to use the default k8s backend)

```bash
docker run -p 8000:8000 -it check_manager
```

Run the following to use the dummy backend

```bash
docker run -p 8000:8000 -it check_manager check-api-server-dummy-prod
```
