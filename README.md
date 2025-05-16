# Resource Health
Repository for EOEPCA Resource Health Building Block

Currently contains:

- Design documentation for the resource health building block (see `docs`)
- Requirements for resource health building block (see `doorstop_reqs_uc`)
- Helm chart for core parts of the resource health building block (see `helm`)
- Helm chart for core parts + dependencies (OpenSearch+Dashboards and OpenTelemetry-collector) (see `resource-health-reference-deployment`)
- Resources for creating and running Python-based health checks (see `pytest-health`)
- APIs to manage health checks, such as creating, scheduling, deleting checks (see `check_manager`)
- Web UI for managing and inspecting checks and their outcomes (see `check_manager_website`)
- A basic mock service to use as a test subject of health checks (see `mock/service`)
- Utilities for loading and running Python plugins (see `plugin-utils`)