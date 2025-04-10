# Check manager

Python library and APIs (REST and CLI) to manage health checks, more specifically allowing to:
* Get check templates
* Get checks
* Create check
* Run check
* Remove check

## Setup

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Run `uv sync` install dependencies and build the project.

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

## Development

To run tests use `uv run pytest`. For type checking use `uv run mypy`. If adding more tests you can use `uv run mypy tests` to type check the tests.

## Docker image

From the current directory build the image with

```bash
docker build -t check_manager -f Dockerfile .
```

Run the image with (to use the default k8s backend)

```bash
docker run -p 8000:8000 -it --env RH_CHECK_API_BASE_URL=http://127.0.0.1:8000 check_manager
```

## Creating cronjob templates

To create your own cronjob template simply make a class with two methods named `get_check_template` and `make_cronjob` in a `.py` file (not named `__init__.py`) and put it in the appropriate directory (`templates` by default). Optionally you can import the abstract base class `CronjobTemplate` from `check_backends.k8s_backend.templates` to inherit from. The benefit to doing this is that you can out the `@override` decorator before the methods and use a type checking tool like `mypy` to check that your methods have the correct names and signatures. Also if the `K8sBackend` finds any partially implemented classes inheriting from `CronjobTemplate` while loading templates it will log warnings indicating there might be spelling mistakes in the method names.
```python
class MyTemplate(CronjobTemplate):
    @override
    def get_check_template(self) -> CheckTemplate:
        """
        Returns an instance of CheckTemplate containng a general information
        about the template and a JSON-schema describing the arguments it accepts.
        """

    @override
    def make_cronjob(
        self,
        template_args,
        schedule,
    ) -> V1CronJob:
        """ Returns a cronjob from the arguments and schedule. """
```
The first function should return a `CheckTemplate` containing name, label, description, and a JSON-schema describing what arguments `make_cronjob` accepts. A simple example could look like this:
```python
    def get_check_template(self):
        return CheckTemplate(
            id=CheckTemplateId("my_template"),
            metadata={
                "label": "my_label",
                "description": "Some general description.",
            },
            arguments={
                "$schema": "http://json-schema.org/draft-07/schema",
                "type": "object",
                "properties": {
                    "health_check.name": {
                        "type": "string",
                    },
                    "options": {
                        "type": "string",
                        "format": "textarea",
                    },
                },
                "required": [
                    "health_check.name",
                ],
            },
        )
```
The function `make_cronjob` should then take a dictionary `template_args` according to your schema, together with a cron expression schedule, and return a `V1CronJob` as defined in `kubernetes_asyncio`. See [documention](https://github.com/tomplus/kubernetes_asyncio/blob/master/kubernetes_asyncio/docs/V1CronJob.md) for more information on how to define cronjobs or take a look at the examples in [src/check_backends/k8s_backend/template_examples](./src/check_backends/k8s_backend/template_examples).

Templates will automatically be loaded from the directories specified when creating the Kubernetes backend: `K8sBackend(template_dirs=["my_templates"])`.
