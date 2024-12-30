# Quick Start

Since the Resource Health BB is currently unauthenticated it does not deploy any public ingresses. Access to any services therefore has to be achieved through port forwarding.

## API endpoints

There are two API endpoints, exposed as seperate services (which will, in the future, be exposed through a single ingress). One endpoint
for managing defined health checks and another for accessing the (OpenTelemetry trace) outcomes of health check executions.

The former (health checks) can be forwarded using
```
$ kubectl [--context=... --namespace=...] port-forward service/resource-health-check-api 8000
```
while the latter can be forwarded by
```
$ kubectl --context=eoepca-develop --namespace=resource-health port-forward service/resource-health-telemetry-api 8080
```

## Skeleton web interface

The skeleton web interface is available on `service/resource-health-web`. It can be forwarded using `kubectl` with
```
$ kubectl [--context=... --namespace=...] port-forward service/resource-health-web 80
```

To work, the web interface requires access to the API endpoints indicated above, which must also be forwarded. Furthermore both
hostnames `resource-health-check-api` and `resource-health-telemetry-api` have to be aliased to `localhost`. This is a temporary
workaround until API endpoints are securely exposed through an endpoint.

## Define health checks

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

Assuming the `resource-health-check-api` service has been forwarded to localhost new health checks can be created as follows.

First get a list of templates provided by the service
```
$ curl -X 'GET' \
  'http://localhost:8000/check_templates/' \
  -H 'accept: application/json'
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
  -H 'accept: application/json' \
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
  -H 'accept: application/json'
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
NOTE that on the EOEPCA development cluster, OpenSearch dashboards are (currently) accessed over HTTP**S** with a self-signed certificate for the internal `svc.kubernetes.local` domain. You should therefore expect your browser to complain about invalid/untrusted/self-signed certificates.
