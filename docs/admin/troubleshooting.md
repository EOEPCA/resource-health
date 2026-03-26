# Troubleshooting

## Website gives 500 error when loading

The recommended approach is this:

1. Open the `Network` tab of your browser developer tools and check which requests give this error. It will either be from Health Check API, or from Telemetry API.
2. Check the K8s logs of that deployment.
3. The most frequent Telemetry API error is something like below
    ```text
    opensearchpy.exceptions.ConnectionError:
    ConnectionError(Cannot connect to host opensearch-cluster-master-headless:9200 ssl:True [SSLCertVerificationError:
    (1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:1010)')])
    caused by: ClientConnectorCertificateError(Cannot connect to host opensearch-cluster-master-headless:9200 ssl:True
    [SSLCertVerificationError: (1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:1010)')])
    ```
    If you see this, it means that OpenSearch certificate has expired. This is perfectly normal and is expected to happen once every few months. It happens because OpenSearch certificates are rotated once in a few months, but the services only read the certificate upon startup, and thus don't pick up the updated certificates. To resolve this, simply restart all services which communicate with OpenSearch:
    * OpenSearch itself
    * OpenSearch Dashboards
    * OpenTelemetry Collector(s) which send traces directly to OpenSearch
    * Telemetry API