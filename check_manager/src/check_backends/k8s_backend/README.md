# Creating cronjob templates

To create your own cronjob template, start by importing `CronjobTemplate` from `check_backends.k8s_backend.templates`. This is a class with two abstract function `get_check_template` and `make_cronjob` that you can override to define your own cronjob template.
```python
class MyTemplate(CronjobTemplate):
    @classmethod
    @override
    def get_check_template(cls) -> CheckTemplate:
        """
        Returns an instance of CheckTemplate containng a general information
        about the template and a JSON-schema describing the arguments it accepts.
        """

    @classmethod
    @override
    def make_cronjob(
        cls,
        template_args,
        schedule,
    ) -> V1CronJob:
        """ Returns a cronjob from the arguments and schedule. """
```
The first function should return a `CheckTemplate` containing name, label, description, and a JSON-schema describing what arguments `make_cronjob` accepts. A simple example could look like this
```python
    def get_check_template(cls):
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
The function `make_cronjob` should then take `template_args` according to your schema, together with a cron expression schedule, and return a `V1CronJob` as defined in `kubernetes_asyncio`. See [documention](https://github.com/tomplus/kubernetes_asyncio/blob/master/kubernetes_asyncio/docs/V1CronJob.md) for more information on how to define cronjobs or take a look at the examples in the `templates` directory.

Templates will automatically be loaded from the directories specified when creating the Kubernetes backend: `k8sBackend(template_dirs=["my_templates"])`.
