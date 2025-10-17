# Python runner image

A simple container image that expects universal paths pointing to a `requirements.txt` and a python script file, e.g. URL, data URL, etc. Data URL allows to encode a file in a URL string, see [Data URL section](#data-url) for details.
When run, it will fetch the two, install the dependencies from `requirements.txt` and execute pytest tests from the file using `pytest [...] scriptname.py`.

Note that the image has universal path support from using [Universal Pathlib package](https://pypi.org/project/universal-pathlib/). So all the filesystems and protocols listed [here](https://github.com/fsspec/universal_pathlib/tree/e3ba0a094d0d2f64a6b9737fd941c72b902d9db7?tab=readme-ov-file#currently-supported-filesystems-and-protocols) are either supported now or the support could be added very quickly (just by adding some dependencies).

## Data URL

Data URLs allow encoding files as URLs. So instead of putting a file somewhere and providing a link to it for the health check definition, you can encode your file in a data URL instead. Data URL is a string `data:text/plain;base64,<data>` where `data` is base64 encoded string. One quick way to see the base64 data encoding and decoding is to use online tools such as [https://www.base64encode.org/](https://www.base64encode.org/) and [https://www.base64decode.org/](https://www.base64decode.org/) respectively.

Note that the data URLs are also supported in browsers, so you can inspect a data URL like `data:text/plain;base64,SGVsbG8gd29ybGQh` by opening it in a browser as if it was any other URL. The above data URL encodes `Hello world!` by the way.

See [Data URL](https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/data) for more.

# Use

Build the image in the "usual" way from the `pytest-health` directory:
```
docker build -t temporary_runner_image:v0.0.1 -f runner-image/Dockerfile .
```

To test out a basic (non-instrumented) check run either serve the image locally (using e.g. `python -m http.server`)
or use [this published test_arxiv_api.py](https://raw.githubusercontent.com/EOEPCA/resource-health/a04ea5211fc60340656a20f45dcc0e9fa40eeee9/pytest-health/lib/other-examples/test_arxiv_api/test_arxiv_api.py) and [requirements.txt file](https://raw.githubusercontent.com/EOEPCA/resource-health/a04ea5211fc60340656a20f45dcc0e9fa40eeee9/pytest-health/lib/other-examples/test_arxiv_api/requirements.txt).

```
docker run --rm --env RH_RUNNER_REQUIREMENTS="https://raw.githubusercontent.com/EOEPCA/resource-health/a04ea5211fc60340656a20f45dcc0e9fa40eeee9/pytest-health/lib/other-examples/test_arxiv_api/requirements.txt" --env RH_RUNNER_SCRIPT="https://raw.githubusercontent.com/EOEPCA/resource-health/a04ea5211fc60340656a20f45dcc0e9fa40eeee9/pytest-health/lib/other-examples/test_arxiv_api/test_arxiv_api.py" temporary_runner_image:v0.0.1
```

The image includes the OpenTelemety instrumentation for PyTest. If you have an OpenTelemetry endpoint accessible on the host machine you can, for example, run
```
docker run --network host --rm --env RH_RUNNER_REQUIREMENTS="https://raw.githubusercontent.com/EOEPCA/resource-health/a04ea5211fc60340656a20f45dcc0e9fa40eeee9/pytest-health/lib/other-examples/test_arxiv_api/requirements.txt" --env RH_RUNNER_SCRIPT="https://raw.githubusercontent.com/EOEPCA/resource-health/a04ea5211fc60340656a20f45dcc0e9fa40eeee9/pytest-health/lib/other-examples/test_arxiv_api/test_arxiv_api.py" temporary_runner_image:v0.0.1
```

It is currently published as `docker.io/eoepca/healthcheck_runner:2.0.0`.

## Pre and post commands

You can set environment variable `RH_RUNNER_RUN_BEFORE` when running the image to execute some command before running health checks.
`RH_RUNNER_RUN_AFTER` is an analogous command to run after running health checks. Note that it will execute regardless if any of the previous commands fail.
If any script command fails (including the before or after commands), the whole script will fail (i.e. have a non-zero exit code)

# Notes

You can use `--suppress-tests-failed-exit-code` from the (preinstalled) `pytest-custom-exit-code` plugin to 
make a failed test not generate a non-zero exit code (useful in Kubernetes to not trigger retries).
