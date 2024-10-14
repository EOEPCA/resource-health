# Quick Start

Since the resource health BB is currently unauthenticated it does not deploy any public ingresses. Access to any services therefore has to be done through port forwarding.

## Skeleton web interface

The skeleton web interface is available on `service/resource-health-web`. It can be forwarded using `kubectl` with
```
kubectl [--context=... --namespace=...] port-forward service/resource-health-web 80
```
and accessed by

- [http://127.0.0.1](http://127.0.0.1) to list recent health check outcomes and
- [http://127.0.0.1/checks](http://127.0.0.1/checks) to see a list of defined health checks

## Define health checks

When using the Helm-chart a set of health checks can be defined using the (Helm) value `healthchecks.checks` (or `resource-health.healthchecks.checks` for the reference deployment chart). It is specified as a list, such as
```yaml
healthchecks:
  [...]
  checks:
  - name: daily-trivial-check
    image:
      repository: docker.io/eoepca/healthcheck_runner
      pullPolicy: IfNotPresent
      tag: "v0.1.0-demo"
    ## Every day at 08:00
    schedule: "0 8 * * *"
    requirements: "https://gist.githubusercontent.com/Jonas-Puksta-Sensmetry/cffc6a422d5bf5af7c4718ec75888950/raw/7e3a24902abd220bd5b3c12c7b3758185db5b13d/requirements.txt"
    script: "https://gist.githubusercontent.com/tilowiklundSensmetry/74dea6500a5bd0b8bbce551249eb6786/raw/f7a614be2809576c4b4b0f3fcc1a1d34ac6af789/trivial_check.py"
    userid: bob
    env:
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: https://opentelemetry-collector:4317
```
The important fields to customise being:
- `name`: A name to recognise the health check
- `schedule`: A cron schedule for when to execute the check
- `requirements`: A HTTP(S) URL to fetch a file requirements.txt file with (additional) Python requirements needed for the health check script
- `script`: A HTTP(S) URL to fetch a PyTest script that expresses the health check

See the [EOEPCA develop deployment for a current example](https://github.com/EOEPCA/eoepca-plus/blob/deploy-develop/argocd/eoepca/resource-health/resource-health.yaml), or to add a health check to the EOEPCA development cluster.

## Accessing the underlying data directly

The underlying OpenSearch database can be accessed through the service `service/opensearch-cluster-master-headless`
```
kubectl [--context=... --namespace=...] port-forward service/opensearch-cluster-master-headless 9200
```

The OpenSearch Dashboards (a.k.a. Kibana for OpenSearch) can be accessed through the service
```
kubectl [--context=... --namespace=...] port-forward service/resource-health-opensearch-dashboards 5601
```
NOTE that on the EOEPCA development cluster, OpenSearch dashboards is (currently) accessed over HTTP**S** with a self-signed certificate for the internal `svc.kubernetes.local` domain. You should therefore expect your browser to complain about invalid/untrusted/self-signed certificates.
