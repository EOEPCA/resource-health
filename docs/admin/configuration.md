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
        In case you want the checks to run on another cluster, you should ensure that sending telemetry to OTel Collector and querying telemetry from OpenSearch is still possible. For OTel Collector, we would recommend to deploy one in the same cluster as the health checks, based on the OTel Collector in the reference deployment [here](https://github.com/EOEPCA/resource-health/blob/5ff09e37f1a5bfcc28c18b867c36184925f21e42/resource-health-reference-deployment/values.yaml#L189). The OTel Collector could just forward everything to the main one (if such exists). For OpenSearch, you need to ensure that query endpoint is accessible, for example by exposing it to the outside.
