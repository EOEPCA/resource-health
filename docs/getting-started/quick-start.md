# Quick Start
<!-- 
Resource Health BB can be deployed with authentication. See [Current deployment in development cluster](#current-deployment-in-development-cluster)

## API endpoints

There are two API endpoints, exposed as separate services (which will, in the future, be exposed through a single ingress). One endpoint
for managing defined health checks and another for accessing the (OpenTelemetry trace) outcomes of health check executions.

The former (health checks) can be forwarded using
```
$ kubectl [--context=... --namespace=...] port-forward service/resource-health-check-api 8000
```
while the latter can be forwarded by
```
$ kubectl [--context=... --namespace=...] port-forward service/resource-health-telemetry-api 8080
```

## Skeleton web interface

The skeleton web interface is available on `service/resource-health-web`. It can be forwarded using `kubectl` with
```
$ kubectl [--context=... --namespace=...] port-forward service/resource-health-web 80
```

To work, the web interface requires access to the API endpoints indicated above, which must also be forwarded. Furthermore both
hostnames `resource-health-check-api` and `resource-health-telemetry-api` have to be aliased to `localhost`. This is a temporary
workaround until API endpoints are securely exposed through an endpoint. -->


## Minimal local deployment

Here is described how to deploy a minimal version of Resource Health BB. Among other things, this means that the deployment isn't secure, doesn't have user management, doesn't have redundancy, and isn't performant.

For more information about what various components of Resource Health do, see [Deployment Overview](https://eoepca.readthedocs.io/projects/resource-health/en/latest/getting-started/deployment-overview/). For a production deployment guide, see [Resource Health Deployment Guide](https://eoepca.readthedocs.io/projects/deploy/en/latest/building-blocks/resource-health/).

!!! note
    The Docker images of Resource Health BB are for `x86_64` processor architecture. The latest image version (the versions used in this deployment guide) also have `arm64` variants. If the cluster is running on `arm64` architecture, append `-arm64` to each image tag to each image `docker.io/eoepca/...` in `resource-health-deployment.yaml`. For example, `docker.io/eoepca/resourcehealth_check_api:2.1.1-b013dbe` should be replaced with `docker.io/eoepca/resourcehealth_check_api:2.1.1-b013dbe-arm64`.

This guide assumes that you have a minikube cluster running locally with a `resource-health` namespace already created. A very similar setup should would with any other Kubernetes clusters, the only different step is how you expose a service to be available from the outside.

1. Clone [Resource Health main repository](https://github.com/EOEPCA/resource-health). The rest of the steps should be executed from `minimal-local-deployment` directory.
2. Deploy a minimal version of OpenSearch. This skips any security, and only deploys one instance. You can deploy it in any other way you see fit. The other components assume an unsecured OpenSearch deployment with `cluster.name` being `opensearch-cluster` and which ingests data at port `9200`.
    1. ```
      helm repo add opensearch https://opensearch-project.github.io/helm-charts/
      helm repo update
      ```
    2. Replace `<strong_password>` with an actual strong password in `opensearch-values.yaml`
    3. ```
      helm install opensearch opensearch/opensearch --version 2.21.0 -f opensearch-values.yaml
      ```
3. Deploy an OpenTelemetry Collector which will gather OpenTelemetry traces and forward them to OpenSearch. You can also deploy this another way if you so choose. The other components assume that `resource-health-opentelemetry-collector:4317` is an unsecured gRPC endpoint to which traces can be sent.
    1. ```
      helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
      helm repo update
      ```
    2. ```
      helm install otelcol open-telemetry/opentelemetry-collector --version 0.101.2 -f otelcol-values.yaml -n resource-health
      ```
4. Deploy Health Check API, Telemetry API, and Web UI
    1. ```
      kubectl apply -f resource-health-service.yaml
      ```
    2. Now you need to expose the service above to outside the cluster. In this case we use `minikube tunnel`, but you'll need to use other means if you're not using minikube. For example you could use an ingress.
      ```
      minikube tunnel (this calls a sudo command so requires password)
      ```
    3. Now you need to find which IP could be used to access the resource health service we deployed. Run
      ```
      kubectl get svc
      ```
      You can see the service external IP in the `LoadBalancer` row. Replace `<service-external-ip>` in `resource-health-deployment.yaml` with it
    4. ```
      kubectl apply -f resource-health-deployment.yaml
      ```

### API endpoints

There are two API endpoints:

- API for managing health checks `http://<service-external-ip>:8000`. Go to `http://<service-external-ip>:8000/docs` to explore the API - this page serves as both documentation and allows you to make HTTP requests to the API.
- API for accessing the (OpenTelemetry trace) outcomes of health check executions `http://<service-external-ip>:8000`.

The APIs are self-documenting - you the base of the APIs is a json file with named links to the main parts.
In particular, you can go to `/docs` route in either API to explore it - that page serves as both documentation and allows you to make HTTP requests to the API.

### Web interface

Available at `http://<service-external-ip>:3000`.

### Basic usage

For the basics of how to use Resource Health BB, see [Basic tutorial for users](../usage/tutorials.md#basic-tutorial-for-users).

<!-- 
### Using Helm values

When using the Helm-chart a set of health checks can be defined using the (Helm) value `healthchecks.checks` (or `resource-health.healthchecks.checks` for the reference deployment chart). It is specified as a list, such as
```yaml
healthchecks:
  [...]
  checks:
  - name: hourly-mockapi-check
    schedule: "0 8 * * *"
    requirements: "https://gist.githubusercontent.com/tilowiklundSensmetry/a9fefe2873b731b483f554607a82deaa/raw/1136a82ca3c8f28b1ad4d895871514185927dd1c/requirements.txt"
    script: "https://raw.githubusercontent.com/EOEPCA/resource-health/refs/tags/v0.1.0-demo/pytest-health/instrumentation/examples/mock_api_check.py"
    env:
      - name: MOCK_API_HOST
        value: http://resource-health-mockapi:5000
```
The important fields to customise being:

- `name`: A name to recognise the health check
- `schedule`: A cron schedule for when to execute the check
- `requirements`: A URL to fetch a file requirements.txt file with (additional) Python requirements needed for the health check script
- `script`: A URL to fetch a PyTest script that expresses the health check
- `env`: to specify a list of environment variables for the health check script.

URLs can be specified by any protocol supported by [fsspec](https://filesystem-spec.readthedocs.io/).

See the [EOEPCA develop deployment for a current example](https://github.com/EOEPCA/eoepca-plus/blob/deploy-develop/argocd/eoepca/resource-health/), or to add a health check to the EOEPCA development cluster.

### Using the API

New health checks can be created as follows.

First get a list of templates provided by the service
```
$ curl -X 'GET' \
  'http://localhost:8000/check_templates/' \
  -H 'accept: application/vnd.api+json'
```
Which should produce JSON-output along the lines of
```json
[
  {
    "id": "default_k8s_template",
    "metadata": {
      "label": "Default Kubernetes template",
      "description": "Default template for checks in the Kubernetes backend."
    },
    "arguments": {
      "$schema": "http://json-schema.org/draft-07/schema",
      "type": "object",
      "properties": {
        "health_check.name": {
          "type": "string"
        },
        "script": {
          "type": "string",
          "format": "textarea"
        },
        "requirements": {
          "type": "string",
          "format": "textarea"
        }
      },
      "required": [
        "health_check.name",
        "script"
      ]
    }
  }
]
```
This tells us that (only) one template is available, having the identifier `default_k8s_template`, expecting
three `string`s: `health_check.name`, `script`, and `requirements`. This template matches (exactly) the pattern used when specifying health checks as part of the (Helm) deployment values.

A new health check can be created by `POST`ing
a body like
```json
{
  "template_id": "default_k8s_template",
  "template_args": {
    "health_check.name" : ...,
    "script": ...,
    "requirements": ...
  },
  "schedule": "0 8 * * *"
}
```
as
```
$ curl -X 'POST' \
  'http://localhost:8000/checks/' \
  -H 'accept: application/vnd.api+json' \
  -H 'Content-Type: application/json' \
  -d '{
     "template_id": ...,
     "template_args": ...,
     "schedule": ...
  }'
```

The list of current checks can be accessed through the same endpoint
```
$ curl -X 'GET' \
  'http://localhost:8000/checks/' \
  -H 'accept: application/vnd.api+json'
```
yielding an output like
```json
[
  {
    "id": "...",
    "metadata": {
      "template_id": "default_k8s_template",
      "template_args": {
        ...
      }
    },
    "schedule": "...",
    "outcome_filter": {
      "resource_attributes": {
        "k8s.cronjob.name": "..."
      }
    }
  },
  ...
]
```
Where:

- `id` represents an internal identifier (in the REST API) used for `DELETE`ing or `PATCH`ing the health check;
- `metadata` contains information such as human readable labels/names as well as provenance (such as the template form which it was produced);
- `schedule` is the CRON-style schedule according to which the health check is executed; and
- `outcome_filter` contains a (OpenTelemetry trace data) filtering criterion for identifying spans pertinent to this health check. 

## Accessing the database directly

The underlying OpenSearch database can be accessed through the service `service/opensearch-cluster-master-headless`
```
kubectl [--context=... --namespace=...] port-forward service/opensearch-cluster-master-headless 9200
```

The OpenSearch Dashboards (a.k.a. Kibana for OpenSearch) can be accessed through the service
```
kubectl [--context=... --namespace=...] port-forward service/resource-health-opensearch-dashboards 5601
```
NOTE that on the EOEPCA development cluster, OpenSearch dashboards are (currently) accessed over HTTP**S** with a self-signed certificate for the internal `svc.kubernetes.local` domain. You should therefore expect your browser to complain about invalid/untrusted/self-signed certificates. -->
