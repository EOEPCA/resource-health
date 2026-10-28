# Development State

Most of the resource health is implemented in a monorepo [EOEPCA/resource-health](https://github.com/EOEPCA/resource-health).

Here is the list of Resource Health components we implemented, where they are implemented, and their implementation status.
Some components (such as OpenSearch and OpenTelemetry Collector) are off-the-shelf open-source implementations.

## Deployment

Resource Health Core HELM Chart is at [EOEPCA/helm-charts-dev/charts/resource-health](https://github.com/EOEPCA/helm-charts-dev/tree/develop/charts/resource-health). It covers the core components of the Resource Health BB, and not the third-party ones.

Resource Health Reference Deployment HELM chart is at [EOEPCA/helm-charts-dev/charts/resource-health-reference-deployment](https://github.com/EOEPCA/helm-charts-dev/tree/develop/charts/resource-health-reference-deployment). It is a complete reference deployment of Resource Health.

For reference, the Resource Health configuration used in the EOEPCA+ development deployment is at [EOEPCA/eoepca-plus/argocd/eoepca/resource-health](https://github.com/EOEPCA/eoepca-plus/tree/deploy-develop/argocd/eoepca/resource-health).

## Health Check API

Implemented at [EOEPCA/resource-health/check_manager](https://github.com/EOEPCA/resource-health/tree/main/check_manager).
Implemented user-facing functionality:

* List health check templates
* List, create, delete, health checks
* Inspect an existing health check
* Run a health check on demand

Implementation details:

* A mechanism to define and use health check templates
* Auth
* Hooks
* Different backends which specify how check management is executed
    * Kubernetes backend
    * REST backend
    * Mock backend
* Different APIs which expose the functionality
    * REST API
    * CLI

Missing features:

* CLI auth

Depends on:

* [Plugin Utils](#plugin-utils) to load and run hooks.
* [Pytest Health](#pytest-health) to execute health checks.
* [EOEPCA+ API Utils](#eoepca-api-utils) for REST API utilities.
* [Python eoepca-security](#python-eoepca-security) to ease using OAuth/OIDC tokens.

## Telemetry API

Implemented at [EOEPCA/python-opentelemetry-access](https://github.com/EOEPCA/python-opentelemetry-access).
Implemented features:

* Auth
* Hooks
* Different backends which specify how to get data in response to a query
    * OpenSearch backend
    * Mock backend
* Different APIs which expose the functionality
    * REST API
    * CLI

Missing features:

* CLI auth

Depends on:

* [OpenTelemetry BetterProto](#opentelemetry-betterproto) to serialize and deserialize OpenTelemetry trace data.
* [Plugin Utils](#plugin-utils) to load and run hooks.
* [EOEPCA+ API Utils](#eoepca-api-utils) for REST API utilities.
* [Python eoepca-security](#python-eoepca-security) to ease using OAuth/OIDC tokens.

## Check Manager Website

Implemented at [EOEPCA/resource-health/check_manager_website](https://github.com/EOEPCA/resource-health/tree/main/check_manager_website). 
Implemented features:

* List, create, delete health checks
* For each check see the run aggregate status
* Inspect an existing health check, and its recent run statuses
* Run a health check on demand
* Inspect the trace of a particular health check run
* Auth

Depends on:

* [Health Check API](#health-check-api) for health check management functionality.
* [Telemetry API](#telemetry-api) for health check run telemetry management functionality.

## Check Alerting

A proof of concept is implemented at [EOEPCA/resource-health/check_alerting](https://github.com/EOEPCA/resource-health/tree/main/check_alerting).
Implemented features:

* Send email notifications to the user for health check runs with an error.

Missing features:

* There is no link from in the email to the failed health check run page in the health check website. This is largely because the health check run trace doesn't currently specify the health check id anywhere (currently `k8s.cronjob.name` coincides with health check id, but that's an implementation detail of the current Kubernetes backend implementation).
* User has no way to unsubscribe from receiving email notifications
* User has no way to specify for which checks they want to receive notifications
* User has no way to specify which email to use for the notifications

Depends on:

* [OpenTelemetry BetterProto](#opentelemetry-betterproto) to serialize and deserialize OpenTelemetry trace data.

## Subcomponents

### OpenTelemetry BetterProto

Implemented at [EOEPCA/opentelemetry-betterproto](https://github.com/EOEPCA/opentelemetry-betterproto).

Features:

* Generates Python code to serialize and deserialize OpenTelemetry trace data
* Supports OTLP and OTLP/JSON data formats of OpenTelemetry

### Pytest Health

Implemented at [EOEPCA/resource-health/pytest-health](https://github.com/EOEPCA/resource-health/tree/main/pytest-health).

Features:

* A Docker image which runs a Python script from a [data url](./usage/tutorials.md#data-url).
* `requirements.txt` is also taken from a [data url](./usage/tutorials.md#data-url).
* Change what setup (if any) runs before the Python script without rebuilding the image.
* Change what setup (if any) runs after the Python script without rebuilding the image.

### Plugin Utils

Helpers to extract and run Python plugins. Implemented at [EOEPCA/resource-health/plugin-utils](https://github.com/EOEPCA/resource-health/tree/main/plugin-utils).

Features:

* Load and extract desired members from Python files in a directory. In practice it's usually used to load hook functions
* Run the hook functions

### EOEPCA+ API Utils

The common code for both [Health Check API](#health-check-api) and [Telemetry API](#telemetry-api) extracted into one place to avoid duplication. Implemented at [EOEPCA/resource-health/eoepca-api-utils](https://github.com/EOEPCA/resource-health/tree/main/eoepca-api-utils).

Features:

* FastAPI utilities such as exceptions
* [JSON:API](https://jsonapi.org/) type definitions

### Python eoepca-security

Implemented at [EOEPCA/python-eoepca-security](https://github.com/EOEPCA/python-eoepca-security).

Features:

* Eases using OAuth/OIDC tokens as forwarded by APISIX in FastAPI
* mitmproxy add-on which can be used to proxy (unauthenticated) requests to a service which requires authentication
