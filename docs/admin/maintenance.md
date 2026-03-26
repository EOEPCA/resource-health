# Maintenance

Administrative and remedial activities to be performed on a running BB instance.

## How to add a new user

Each new user needs to be granted permissions to make use of the Resource Health BB. Only grant the permissions appropriate for that user.

* Update Health Check API Hooks to give the user permission to create health from the health check templates appropriate for that user. See [Hooks Tutorial](../usage/tutorials.md#hooks-tutorial) for how to do that.
* Give the user permission to inspect their health check telemetry by granting them role `own_trace_data_access` in OpenSearch. See [Document-level security](./configuration.md#document-level-security) for more about that role.
* Give the user permission to inspect their health check telemetry in OpenSearch dashboards by granting them `dashboards_access_ro` role in OpenSearch.
