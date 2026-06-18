# Deployment overview

This is a high level deployment overview. For precise deployment instruction see [Resource Health Deployment Guide](https://eoepca.readthedocs.io/projects/deploy/en/stable/building-blocks/resource-health/).

This document outlines what the current and planned deployment structure of the Resource Health BB is.

The Resource Health BB in the default configuration relies on:

- (A) Identity provider compatible with OpenID Connect
- (B) OpenSearch database such that (for specified indices) the end-users have read/write permissions and the Resource Health BB can use/forward tokens from the end-user
- (C) A deployment of the OpenTelemetry collector that can write to (B) via its REST API
- (D) A Kubernetes API endpoint with associated Kubernetes namespaces such that the Resource Health BB has a service account that can create CronJob resources and Secrets
- (E) A deployment of a number of stateless web services that implement APIs and user interfaces which
    - Authenticate (end-users) against the identity provider (A)
    - Read data from the OpenSearch database (B)
    - Create and/or run CronJob resources through (D)

Auth is coordinated between Resource Health website, APIs, and OpenSearch. When user goes to the website, he needs to authenticate with an auth proxy. The user identity is then used with requests to Resource Health APIs, which in turn use it for accessing data in OpenSearch. Resource Health API authentication and authorization is configured through hooks, see [Hooks Tutorial](../usage/tutorials.md#hooks-tutorial).

The "core" components in (E) can be deployed through the Helm-chart in the [`resource-health` directory of the Helm Charts Dev repository](https://github.com/EOEPCA/helm-charts-dev/tree/e0dd33dd8d78cb9e23e5383c1788aa8b0ba235f1/charts/resource-health).

There is also a [full reference deployment chart](https://github.com/EOEPCA/helm-charts-dev/tree/e0dd33dd8d78cb9e23e5383c1788aa8b0ba235f1/charts/resource-health-reference-deployment) that includes reference deployments of (B) and (C) as well as (E) (but not (A)).
