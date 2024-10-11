# Skeleton Web UI

This directory contains a very basic skeleton UI that exposes some simple information
about a resource health building block proof-of-concept deployment.
**It serves mainly to ensure the demo is properly deployed and running and is not intended to representative of the future UI**.

WARNING: There is currently no authorization or authentication included (so do not expose)!

# Use

You can build a container image the usual way, e.g.
```
docker build -t tmp_resourcehealth_web:local-test .
```

The image starts the application on a **yarn dev server** on port 3000, and requires
specifying the OpenSearch endpoint and credentials, along the lines of
```
docker run --rm --net host -v <PATH_TO_CLIENT_CERTIFICATES>:/client-tls -e OPENSEARCH_ENDPOINT=https://localhost:9200 -e CA_PATH=/client-tls/<CA_CERT> -e CLIENT_CERT_PATH=/client-tls/<CLIENT_CERT> -e CLIENT_KEY_PATH=/client-tls/<CLIENT_KEY> tmp_resourcehealth_web:local-test
```

A list of most recent test executions is available on the server root (e.g. `http://localhost:3000`).

The image is currently published under `docker.io/eoepca/resourcehealth_web`.
