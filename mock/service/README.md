# Mock service

This directory contains a mock service that serve as a test subject for health checks.
It is a flask web service with a single endpoint (`/`) that returns the value of a random "die-roll".

# Use

Install the requirements from `requirements.txt`. To run *without* instrumentation use
```
flask --app app.py run --host 0.0.0.0
```
to run *with* instrumentation use
```
opentelemetry-instrument --traces_exporter otlp --logs_exporter otlp flask --app app.py run --host 0.0.0.0
```
either of which will start a server listening on `0.0.0.0:5000`.

The ontainer image can be built the usual way, e.g.
```
docker build -t tmp_mock_service:v0.0.1 .
```
so that you can run a server on the host network with something like
```
docker run --rm -it --net host tmp_mock_service:v0.0.1
```

The image is currently published as `docker.io/tilowiklundsensmetry/mock_service`.