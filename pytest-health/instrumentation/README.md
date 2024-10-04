# PyTest instrumentation for OpenTelemetry

Currently mostly a copy of https://github.com/chrisguidry/pytest-opentelemetry/blob/main/src/pytest_opentelemetry/instrumentation.py

Will either transition to use/contribute to/fork:

- https://github.com/chrisguidry/pytest-opentelemetry (repo above)
- https://github.com/kuisathaverat/pytest_otel/
- https://github.com/s4v4g3/otel-extensions-pytest

Ideally integrating with the [OpenTelemetry Python agent](https://opentelemetry.io/docs/zero-code/python/).

# Use

Install requirements, preferrably in a venv (`python -m venv .venv; source .venv/bin/activate; pip install -r requirements.txt`). You may want to make sure that you can run the test **uninstrumented** as `pytest examples/trivial_check.py` before continuing.

To execute with instrumentation, you need something to listen for opentelemetry traces. To get a simple graphical view you can use `otel-desktop-viewer` using the [following instructions](https://github.com/ojkelly/otel-desktop-viewer/tree/25713e1699f7d02d51b691ce3cce9db8bebb25d4?tab=readme-ov-file#via-go-install). Once running, open your browser to `http://localhost:8000`.

You should now be able to run the trivial test example **with** instrumentation as follows:
```
pytest --export-traces examples/triv
ial_check.py
```
If you check your browser window again, you should see a trace with the following structure
```
test run
47.277 ms

    examples/trivial_check.py::test_which_will_fail
    34.214 ms

        examples/trivial_check.py::test_which_will_fail::setup
        159.488 μs

        examples/trivial_check.py::test_which_will_fail::call
        359.424 μs

        examples/trivial_check.py::test_which_will_fail::teardown
        187.392 μs

    examples/trivial_check.py::test_which_wont_fail
    909.312 μs

        examples/trivial_check.py::test_which_wont_fail::setup
        102.400 μs

        examples/trivial_check.py::test_which_wont_fail::call
        95.744 μs

        examples/trivial_check.py::test_which_wont_fail::teardown
        157.952 μs
```
