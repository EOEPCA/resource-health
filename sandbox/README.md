# Tiny certificate example

This example consists of four resources:

- `resource-health-test-certificate.yaml`: a Certificate (requested from the cluster issuer)
- `resource-health-test-server-pod.yaml`: a pod running a Hello World Flask application on HTTPS, using the above certificate
- `resource-health-test-service.yaml`: a service for exposing the above Flask application
- `resource-health-test-client-pod.yaml`: a pod running `curl` against the service every 5s

The setup mounts the certificate secrets in the server-pod and mounts+trust the ca certificate in the client-pod.

NOTE: `flaskapp.py` is added for reference, it is included verbatim in the server resource yaml as compressed base64.
