# Python runner image

A simple container image that expects URLs pointing to a `requirements.txt` and a python script file. 
When run, it will fetch the two, install the dependencies from `requirements.txt` and execute a user provided 
command (typically `python scriptname.py [...]` or `pytest [...] scriptname.py`).

Notes:
- The "interface" is likely to change in the future
- Currently URLs are not optional (planned to add support for URLs pointing to local files though)

# Use

Build the image in the "usual" way from the `pytest-health` directory:
```
docker build -t temporary_runner_image:v0.0.1 -f runner-image/Dockerfile .
```

To test out a basic (non-instrumented) check run either serve the image locally (using e.g. `python -m http.server`)
or use [this published trivial_check.py](https://gist.githubusercontent.com/tilowiklundSensmetry/74dea6500a5bd0b8bbce551249eb6786/raw/f7a614be2809576c4b4b0f3fcc1a1d34ac6af789/trivial_check.py) and [requirements.txt file](https://gist.githubusercontent.com/Jonas-Puksta-Sensmetry/cffc6a422d5bf5af7c4718ec75888950/raw/7e3a24902abd220bd5b3c12c7b3758185db5b13d/requirements.txt).

```
docker run --rm --env RESOURCE_HEALTH_RUNNER_REQUIREMENTS="https://gist.githubusercontent.com/Jonas-Puksta-Sensmetry/cffc6a422d5bf5af7c4718ec75888950/raw/7e3a24902abd220bd5b3c12c7b3758185db5b13d/requirements.txt" --env RESOURCE_HEALTH_RUNNER_SCRIPT="https://gist.githubusercontent.com/tilowiklundSensmetry/74dea6500a5bd0b8bbce551249eb6786/raw/f7a614be2809576c4b4b0f3fcc1a1d34ac6af789/trivial_check.py" temporary_runner_image:v0.0.1
```

The image includes the OpenTelemety instrumentation for PyTest. If you have an OpenTelemetry endpoint accessible on the host machine you can, for example, run
```
docker run --network host --rm --env RESOURCE_HEALTH_RUNNER_REQUIREMENTS="https://gist.githubusercontent.com/Jonas-Puksta-Sensmetry/cffc6a422d5bf5af7c4718ec75888950/raw/7e3a24902abd220bd5b3c12c7b3758185db5b13d/requirements.txt" --env RESOURCE_HEALTH_RUNNER_SCRIPT="https://gist.githubusercontent.com/tilowiklundSensmetry/74dea6500a5bd0b8bbce551249eb6786/raw/f7a614be2809576c4b4b0f3fcc1a1d34ac6af789/trivial_check.py" temporary_runner_image:v0.0.1
```

It is currently published as `docker.io/tilowiklundsensmetry/healthcheck`.

# Notes

You can use `--suppress-tests-failed-exit-code` from the (preinstalled) `pytest-custom-exit-code` plugin to 
make a failed test not generate a non-zero exit code (useful in Kubernetes to not trigger retries).
