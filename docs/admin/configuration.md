# Configuration

How the BB is configured - with examples etc.

## How to put health checks into different namespaces

In the reference deployment, all health checks are in `resource-health` namespace, together with all the other parts of Resource Health BB, such as Check API, Telemetry API, OpenSearch, OpenTelemetry (OTel) Collector, etc.  
It could be useful to put health checks into separate namespaces, for example, to have a separate namespace for each user (or user group). You might also wish to run the health checks in a separate (virtual) cluster. The steps below will focus on the use case of putting health checks into per-user namespaces, with some notes on how to run them in a different (virtual) cluster. It should not be difficult to adapt this to other setups.

How to put the checks into per-user namespaces:

1. Create a namespace for each user
2. Implement `get_k8s_namespace` hook to get the namespace based on `userid` (see [Hooks Tutorial](../usage/tutorials.md#hooks-tutorial))

    !!! info
        In case you want the checks to run on another cluster, you should also implement `get_k8s_config` to return an appropriate K8s config.

3. Now we need to ensure that the health checks can still communicate with the other parts of Resource Health. That means sending the telemetry to OTel Collector, and querying the previous telemetry from OpenSearch. We need to use Fully Qualified Domain Name (FQDN) for both OTel Collector and OpenSearch endpoint. Specifically, use FQDN for `DEFAULT_COLLECTOR_URL_NO_PROTOCOL` and `DEFAULT_PROXY_REMOTE_DOMAIN` [here](https://github.com/EOEPCA/eoepca-plus/blob/b1bb06b98abf9bf68b4de7cc95a710862c356be6/argocd/eoepca/resource-health/resource-health.yaml#L193). Alternatively, use FQDN for `collector_url_no_protocol` and `proxy_remote_domain` parameters to `simple_runner_template` function for each check template [here](https://github.com/EOEPCA/eoepca-plus/blob/b1bb06b98abf9bf68b4de7cc95a710862c356be6/argocd/eoepca/resource-health/resource-health.yaml#L452). So `collector_url_no_protocol` should be `resource-health-opentelemetry-collector.<collector-namespace>.<internal-domain>:4317`, for example `resource-health-opentelemetry-collector.resource-health.svc.cluster.local:4317` for the reference deployment. `proxy_remote_domain` should be `https://opensearch-cluster-master-headless.<opensearch-namespace>.<internal-domain>:9200`.

    !!! info
        In case you want the checks to run on another cluster, you should ensure that sending telemetry to OTel Collector and querying telemetry from OpenSearch is still possible. For OTel Collector, we would recommend to deploy one in the same cluster as the health checks, based on the OTel Collector in the reference deployment [here](https://github.com/EOEPCA/helm-charts-dev/tree/e0dd33dd8d78cb9e23e5383c1788aa8b0ba235f1/charts/resource-health-reference-deployment/values.yaml#L189). The OTel Collector could just forward everything to the main one (if such exists). For OpenSearch, you need to ensure that query endpoint is accessible, for example by exposing it to the outside.

## Auth

### OpenID Connect

Resource Health BB is designed to work with any OpenID Provider. To integrate with you OpenID Provider you just need to point OpenSearch, Health Check API, and Telemetry API to it.  
Specifically, you need to:

* Configure OpenSearch to use your OpenID Provider by following [this](https://docs.opensearch.org/latest/security/authentication-backends/openid-connect/#configure-openid-connect-integration). See an example [here](https://github.com/EOEPCA/eoepca-plus/blob/b1bb06b98abf9bf68b4de7cc95a710862c356be6/argocd/eoepca/resource-health/resource-health.yaml#L60).
* Set `OPEN_ID_CONNECT_URL` and `OPEN_ID_CONNECT_AUDIENCE` environment variables [here](https://github.com/EOEPCA/eoepca-plus/blob/b1bb06b98abf9bf68b4de7cc95a710862c356be6/argocd/eoepca/resource-health/resource-health.yaml#L189) for Health Check Api, and [here](https://github.com/EOEPCA/eoepca-plus/blob/b1bb06b98abf9bf68b4de7cc95a710862c356be6/argocd/eoepca/resource-health/resource-health.yaml#L99) for Telemetry API.

### Alternative Auth Schemes

To use some other auth scheme (such as basic HTTP auth), you need to:

* Configure OpenSearch authentication, see [here](https://docs.opensearch.org/latest/security/configuration/configuration/#authentication).
* Implement Health Check API hooks `get_fastapi_security` and `on_auth` based on examples [here](https://github.com/EOEPCA/resource-health/tree/9c9444b6eca420e3d81147d24c3ff3e2b7d956a4/check_manager/example_hooks).
* Implement Telemetry API hooks `get_fastapi_security`, `on_auth`, and `get_opensearch_config` based on the example [here](https://github.com/EOEPCA/python-opentelemetry-access/blob/542cd1ca7378bb67460c4309bcb5fbfd0583396d/example_hooks/oidc_auth/auth_hooks.py).
* For health checks to be able to access telemetry using alternative authentication methods:
    * Create a new Docker image which launches an appropriately configured mitmproxy based on [this](https://github.com/EOEPCA/python-eoepca-security/blob/87cc35c7e9e2fc23376a49d50a8553c951762ff9/Dockerfile.mitmproxy).
    * Update the health check template for accessing telemetry to use the new image based on [this](https://github.com/EOEPCA/resource-health/blob/9c9444b6eca420e3d81147d24c3ff3e2b7d956a4/check_manager/src/check_backends/k8s_backend/template_utils/utils.py#L180) and [this](https://github.com/EOEPCA/resource-health/blob/9c9444b6eca420e3d81147d24c3ff3e2b7d956a4/check_manager/src/check_backends/k8s_backend/template_utils/utils.py#L325C5-L325C27).

## OpenSearch

OpenSearch configuration for the reference deployment is defined [here](https://github.com/EOEPCA/helm-charts-dev/tree/e0dd33dd8d78cb9e23e5383c1788aa8b0ba235f1/charts/resource-health-reference-deployment/values.yaml#L342)

### Index

Currently all the health check telemetry is written to `ss4o_traces-default-namespace` index. The index is created by [OTel Collector OpenSearch exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/opensearchexporter#readme). In particular, this means that the index will not exist until the first health check telemetry gets to OpenSearch.

!!! info
    `ss4o_traces-default-namespace` index name is generated by the formula by OTel Collector OpensSearch exporter, see [here](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/opensearchexporter#indexing-options). So to change the index name you need to:

    * Update the OpenSearch Exporter configuration [here](https://github.com/EOEPCA/helm-charts-dev/tree/e0dd33dd8d78cb9e23e5383c1788aa8b0ba235f1/charts/resource-health-reference-deployment/values.yaml#L203).
    * Update [document-level security](#document-level-security) filter to the new namespace.
    * Point Telemetry API to the new index [here](https://github.com/EOEPCA/eoepca-plus/blob/b38fb5fc191e8e9e40fcce5448a02d72d0f95a4b/argocd/eoepca/resource-health/resource-health.yaml#L103).
    * Point health checks which use previous telemetry to the new index [here](https://github.com/EOEPCA/eoepca-plus/blob/b38fb5fc191e8e9e40fcce5448a02d72d0f95a4b/argocd/eoepca/resource-health/resource-health.yaml#L199).

You should also consider doing index management optimized for data streams, such as rotating backing indices, deleting old data, etc., see [Data Streams](https://docs.opensearch.org/latest/im-plugin/data-streams/) and [Index State Management](https://docs.opensearch.org/latest/im-plugin/ism/index) for more.

### Document-level security

Each trace is tagged with `user.id` of the user who created the check. To give a user access to telemetry annotated with their `user.id`, give the user the role `own_trace_data_access`, which is defined [here](https://github.com/EOEPCA/helm-charts-dev/tree/e0dd33dd8d78cb9e23e5383c1788aa8b0ba235f1/charts/resource-health-reference-deployment/values.yaml#L449). This uses [document-level security](https://docs.opensearch.org/latest/security/access-control/document-level-security/) feature of OpenSearch.
<!-- TODO: perhaps mention that only the telemetry reading user user authentication. Sending telemetry to the collector as far as I remember requires no authentication, but the collector is only available from inside the cluster -->

!!! info
    The current `user.id` annotation is meant to signal who is allowed to view the health check telemetry. For a different or more complex security model, you would need to tag the OTel traces with identifier(s) to be used in authorization decisions, and to create a document-level-security role similar to [this](https://github.com/EOEPCA/helm-charts-dev/tree/e0dd33dd8d78cb9e23e5383c1788aa8b0ba235f1/charts/resource-health-reference-deployment/values.yaml#L449), but with a different filtering condition.

