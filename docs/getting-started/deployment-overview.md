# Deployment overview

This document outlines what the current and planned deployment structure of the Resource Health BB is.

The Resource Health BB in the default configuration is intended to rely on:

- (A) Identity provider compatible with OpenID Connect
- (B) OpenSearch database such that (for specified indices)
  - EITHER end-users have read/write permissions and the Resource Health BB can use/forward tokens from the end-user
  - OR the Resource Health BB has a service account on the OpenSearch database 
- (C) A deployment of the OpenTelemtry collector that can write to (B) via its REST api
- (D) A Kubernetes API endpoint with associated Kubernetes namespaces such that
  - EITHER end-users have the right to create CronJob resources and Secrets and the Resource Health BB can use/forward tokens from the end-user
  - OR the Resource Health BB has a service account that can create CronJob resources and Secrets
- (E) A deployment of a number of stateless web services that implement APIs and user interfaces which
  - Authenticate (end-users) against the identity provider (A)
  - Read data from the OpenSearch database (B)
  - Create and/or run CronJob resources through (D)

As of the time of writing, the Resource Health BB demo is essentially unauthenticated, relying on mTLS
for authorization between components.

The "core" components in (E) can be deployed through the Helm-chart in the [`helm` direcotry of the Resource Health repository](https://github.com/EOEPCA/resource-health/tree/main/helm).

There is also a [full reference deployment chart](https://github.com/EOEPCA/resource-health/tree/main/resource-health-reference-deployment) that includes reference deployments of (B) and (C) as well as (E) (but not (A)).