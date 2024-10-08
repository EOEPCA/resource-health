## Based on:
## https://github.com/chrisguidry/pytest-opentelemetry/blob/main/src/pytest_opentelemetry/instrumentation.py
## (under MIT License)

# Copyright (c) 2022 Chris Guidry
#
# Copyright (c) 2024 UAB Sensmetry
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import warnings

with warnings.catch_warnings(action="ignore"):
    import os
    from typing import Any, Dict, Generator, Optional, Union
    import pytest
    from _pytest.config import Config
    from _pytest.fixtures import FixtureDef, FixtureRequest, SubRequest
    from _pytest.main import Session
    from _pytest.nodes import Item, Node
    from _pytest.reports import TestReport
    from _pytest.runner import CallInfo
    from opentelemetry import propagate, trace
    from opentelemetry.context.context import Context
    from opentelemetry.sdk.resources import OTELResourceDetector, Resource, ResourceDetector
    from opentelemetry.semconv.trace import SpanAttributes
    from opentelemetry.semconv.resource import ResourceAttributes
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry_container_distro import (
        OpenTelemetryContainerConfigurator,
        OpenTelemetryContainerDistro,
    )
    import subprocess


from _pytest.config.argparsing import Parser


def pytest_addoption(parser: Parser) -> None:
    group = parser.getgroup("pytest-opentelemetry", "OpenTelemetry for test runs")
    group.addoption(
        "--export-traces",
        action="store_true",
        default=False,
        help=(
            "Enables exporting of OpenTelemetry traces via OTLP, by default to "
            "http://localhost:4317.  Set the OTEL_EXPORTER_OTLP_ENDPOINT environment "
            "variable to specify an alternative endpoint."
        ),
    )
    group.addoption(
        "--trace-parent",
        action="store",
        default=None,
        help=(
            "Specify a trace parent for this pytest run, in the form of a W3C "
            "traceparent header, like "
            "00-1234567890abcdef1234567890abcdef-fedcba0987654321-01.  If a trace "
            "parent is provided, this test run will appear as a span within that "
            "trace.  If it is omitted, this test run will start a new trace."
        ),
    )
    group.addoption(
        "--user-id", action="store", default=None, help="User who runs these tests"
    )


def pytest_configure(config: Config) -> None:
    if config.pluginmanager.has_plugin("xdist"):
        config.pluginmanager.register(XdistOpenTelemetryPlugin())
    else:
        config.pluginmanager.register(OpenTelemetryPlugin())


Attributes = Dict[str, Union[str, bool, int, float]]

tracer = trace.get_tracer("pytest-opentelemetry")


class CodebaseResourceDetector(ResourceDetector):
    """Detects OpenTelemetry Resource attributes for an operating system process,
    providing the `process.*` attributes"""

    @staticmethod
    def get_codebase_name() -> str:
        # TODO: any better ways to guess the name of the codebase?
        # TODO: look into methods for locating packaging information
        return os.path.split(os.getcwd())[-1]

    @staticmethod
    def get_codebase_version() -> str:
        if not os.path.exists(".git"):
            return "[unknown: not a git repository]"

        try:
            version = subprocess.check_output(["git", "rev-parse", "HEAD"])
        except Exception as exception:  # pylint: disable=broad-except
            return f"[unknown: {str(exception)}]"

        return version.decode().strip()

    def detect(self) -> Resource:
        return Resource(
            {
                ResourceAttributes.SERVICE_NAME: self.get_codebase_name(),
                ResourceAttributes.SERVICE_VERSION: self.get_codebase_version(),
            }
        )


class OpenTelemetryPlugin:
    """A pytest plugin which produces OpenTelemetry spans around test sessions and
    individual test runs."""

    @property
    def session_name(self) -> str:
        # Lazy initialise session name
        if not hasattr(self, "_session_name"):
            self._session_name = os.environ.get("PYTEST_RUN_NAME", "test run")
        return self._session_name

    @session_name.setter
    def session_name(self, name: str) -> None:
        self._session_name = name

    @classmethod
    def get_trace_parent(cls, config: Config) -> Optional[Context]:
        if trace_parent := config.getvalue("--trace-parent"):
            return propagate.extract({"traceparent": trace_parent})

        if trace_parent := os.environ.get("TRACEPARENT"):
            return propagate.extract({"traceparent": trace_parent})

        return None

    @classmethod
    def try_force_flush(cls) -> bool:
        provider = trace.get_tracer_provider()

        # Not all providers (e.g. ProxyTraceProvider) implement force flush
        if hasattr(provider, "force_flush"):
            provider.force_flush()
            return True
        else:
            return False

    def pytest_configure(self, config: Config) -> None:
        self.trace_parent = self.get_trace_parent(config)
        self.user_id = config.getvalue("--user-id")

        # This can't be tested both ways in one process
        if config.getoption("--export-traces"):  # pragma: no cover
            OpenTelemetryContainerDistro().configure()

        configurator = OpenTelemetryContainerConfigurator()
        configurator.resource_detectors.append(CodebaseResourceDetector())
        configurator.resource_detectors.append(OTELResourceDetector())
        configurator.configure()

    def pytest_sessionstart(self, session: Session) -> None:
        self.session_span = tracer.start_span(
            self.session_name,
            context=self.trace_parent,
            attributes={"pytest.span_type": "run", "user.id": self.user_id},
        )
        self.has_error = False

    def pytest_sessionfinish(self, session: Session) -> None:
        self.session_span.set_status(
            StatusCode.ERROR if self.has_error else StatusCode.OK
        )

        self.session_span.end()
        self.try_force_flush()

    def _attributes_from_item(self, item: Item) -> Dict[str, Union[str, int]]:
        filepath, line_number, _ = item.location
        attributes: Dict[str, Union[str, int]] = {
            SpanAttributes.CODE_FILEPATH: filepath,
            SpanAttributes.CODE_FUNCTION: item.name,
            "test.case.name": item.name,
            "pytest.nodeid": item.nodeid,
            "pytest.span_type": "test",
        }
        # In some cases like tavern, line_number can be 0
        if line_number:
            attributes[SpanAttributes.CODE_LINENO] = line_number
        return attributes

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item: Item) -> Generator[None, None, None]:
        context = trace.set_span_in_context(self.session_span)
        with tracer.start_as_current_span(
            item.nodeid,
            attributes=self._attributes_from_item(item),
            context=context,
        ):
            yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item: Item) -> Generator[None, None, None]:
        with tracer.start_as_current_span(
            f"{item.nodeid}::setup",
            attributes=self._attributes_from_item(item),
        ):
            yield

    def _attributes_from_fixturedef(
        self, fixturedef: FixtureDef
    ) -> Dict[str, Union[str, int]]:
        return {
            SpanAttributes.CODE_FILEPATH: fixturedef.func.__code__.co_filename,
            SpanAttributes.CODE_FUNCTION: fixturedef.argname,
            SpanAttributes.CODE_LINENO: fixturedef.func.__code__.co_firstlineno,
            "pytest.fixture_scope": fixturedef.scope,
            "pytest.span_type": "fixture",
        }

    def _name_from_fixturedef(self, fixturedef: FixtureDef, request: FixtureRequest):
        if fixturedef.params and "request" in fixturedef.argnames:
            try:
                parameter = str(request.param)
            except Exception:
                parameter = str(
                    request.param_index if isinstance(request, SubRequest) else "?"
                )
            return f"{fixturedef.argname}[{parameter}]"
        return fixturedef.argname

    @pytest.hookimpl(hookwrapper=True)
    def pytest_fixture_setup(
        self, fixturedef: FixtureDef, request: FixtureRequest
    ) -> Generator[None, None, None]:
        with tracer.start_as_current_span(
            name=f"{self._name_from_fixturedef(fixturedef, request)} setup",
            attributes=self._attributes_from_fixturedef(fixturedef),
        ):
            yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item: Item) -> Generator[None, None, None]:
        with tracer.start_as_current_span(
            name=f"{item.nodeid}::call",
            attributes=self._attributes_from_item(item),
        ):
            yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item: Item) -> Generator[None, None, None]:
        with tracer.start_as_current_span(
            name=f"{item.nodeid}::teardown",
            attributes=self._attributes_from_item(item),
        ):
            # Since there is no pytest_fixture_teardown hook, we have to be a
            # little clever to capture the spans for each fixture's teardown.
            # The pytest_fixture_post_finalizer hook is called at the end of a
            # fixture's teardown, but we don't know when the fixture actually
            # began tearing down.
            #
            # Instead start a span here for the first fixture to be torn down,
            # but give it a temporary name, since we don't know which fixture it
            # will be. Then, in pytest_fixture_post_finalizer, when we do know
            # which fixture is being torn down, update the name and attributes
            # to the actual fixture, end the span, and create the span for the
            # next fixture in line to be torn down.
            self._fixture_teardown_span = tracer.start_span("fixture teardown")
            yield

        # The last call to pytest_fixture_post_finalizer will create
        # a span that is unneeded, so delete it.
        del self._fixture_teardown_span

    @pytest.hookimpl(hookwrapper=True)
    def pytest_fixture_post_finalizer(
        self, fixturedef: FixtureDef, request: SubRequest
    ) -> Generator[None, None, None]:
        """When the span for a fixture teardown is created by
        pytest_runtest_teardown or a previous pytest_fixture_post_finalizer, we
        need to update the name and attributes now that we know which fixture it
        was for."""

        # If the fixture has already been torn down, then it will have no cached
        # result, so we can skip this one.
        if fixturedef.cached_result is None:
            yield
        # Passing `-x` option to pytest can cause it to exit early so it may not
        # have this span attribute.
        elif not hasattr(self, "_fixture_teardown_span"):  # pragma: no cover
            yield
        else:
            # If we've gotten here, we have a real fixture about to be torn down.
            name = f"{self._name_from_fixturedef(fixturedef, request)} teardown"
            self._fixture_teardown_span.update_name(name)
            attributes = self._attributes_from_fixturedef(fixturedef)
            self._fixture_teardown_span.set_attributes(attributes)
            yield
            self._fixture_teardown_span.end()

        # Create the span for the next fixture to be torn down. When there are
        # no more fixtures remaining, this will be an empty, useless span, so it
        # needs to be deleted by pytest_runtest_teardown.
        self._fixture_teardown_span = tracer.start_span("fixture teardown")

    @staticmethod
    def pytest_exception_interact(
        node: Node,
        call: CallInfo[Any],
        report: TestReport,
    ) -> None:
        excinfo = call.excinfo
        assert excinfo
        assert isinstance(excinfo.value, BaseException)

        test_span = trace.get_current_span()

        test_span.record_exception(
            # Interface says Exception, but BaseException seems to work fine
            # This is needed because pytest's Failed exception inherits from
            # BaseException, not Exception
            exception=excinfo.value,  # type: ignore[arg-type]
            attributes={
                SpanAttributes.EXCEPTION_STACKTRACE: str(report.longrepr),
            },
        )
        test_span.set_status(
            Status(
                status_code=StatusCode.ERROR,
                description=f"{excinfo.type}: {excinfo.value}",
            )
        )

    def pytest_runtest_logreport(self, report: TestReport) -> None:
        if report.when != "call":
            return

        has_error = report.outcome == "failed"
        status_code = StatusCode.ERROR if has_error else StatusCode.OK
        self.has_error |= has_error
        test_span = trace.get_current_span()
        test_span.set_status(status_code)
        test_span.set_attribute(
            "test.case.result.status", "fail" if has_error else "pass"
        )


try:
    from xdist.workermanage import WorkerController  # pylint: disable=unused-import
except ImportError:  # pragma: no cover
    WorkerController = None


class XdistOpenTelemetryPlugin(OpenTelemetryPlugin):
    """An xdist-aware version of the OpenTelemetryPlugin"""

    @classmethod
    def get_trace_parent(cls, config: Config) -> Optional[Context]:
        if workerinput := getattr(config, "workerinput", None):
            return propagate.extract(workerinput)

        return super().get_trace_parent(config)

    def pytest_configure(self, config: Config) -> None:
        super().pytest_configure(config)
        worker_id = getattr(config, "workerinput", {}).get("workerid")
        self.session_name = (
            f"test worker {worker_id}" if worker_id else self.session_name
        )

    def pytest_configure_node(self, node: WorkerController) -> None:  # pragma: no cover
        with trace.use_span(self.session_span, end_on_exit=False):
            propagate.inject(node.workerinput)

    def pytest_xdist_node_collection_finished(node, ids):  # pragma: no cover
        super().try_force_flush()
