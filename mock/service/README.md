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
either of which will start a server listening on http://0.0.0.0:5000/.

On MacOS that port is most likely already in use, so you could append argument `--port 5001` to start a server listening on port 5001 instead.

The container image can be built the usual way, e.g.
```
docker build -t mock_service .
```
so that you can run a server on the host network with something like
```
docker run -p 5000:5000 -it mock_service
```

The image is currently published as `docker.io/eoepca/mock_service:2.0.0`.