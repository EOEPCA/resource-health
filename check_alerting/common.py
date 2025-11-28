from os import environ
from typing import MutableMapping, cast

from dotenv import load_dotenv
from opentelemetry_betterproto.opentelemetry.proto.collector.trace.v1 import (
    ExportTraceServiceRequest,
)
from opentelemetry_betterproto.opentelemetry.proto.trace.v1 import ResourceSpans

from proto import TraceInfo, TraceInfoStatusCode

type MutableMappingBytes = MutableMapping[str | bytes, bytes]

# Cast is necessary as mypy incorrectly considers TraceInfoStatusCode.RECEIVING to be int
# This is a known issue https://github.com/danielgtaylor/python-betterproto/issues/616
TRACE_INFO_STATUS_CODE_RECEIVING: TraceInfoStatusCode = cast(
    TraceInfoStatusCode, TraceInfoStatusCode.RECEIVING
)
TRACE_INFO_STATUS_CODE_PROCESSING: TraceInfoStatusCode = cast(
    TraceInfoStatusCode, TraceInfoStatusCode.PROCESSING
)
TRACE_INFO_STATUS_CODE_PROCESSED: TraceInfoStatusCode = cast(
    TraceInfoStatusCode, TraceInfoStatusCode.PROCESSED
)

# Load environment variables from .env file
load_dotenv()


def get_env_var_or_throw(name: str) -> str:
    value = environ.get(name)
    if value is None:
        raise ValueError(f"Environment variable {name} must be set")
    return value


ERROR_TRACES_FILE = get_env_var_or_throw("ERROR_TRACES_FILE")
TRACE_INFOS_FILE = get_env_var_or_throw("TRACE_INFOS_FILE")


def get_trace_info(
    trace_to_info: MutableMappingBytes, trace_id: str
) -> TraceInfo | None:
    trace_info_serialized = trace_to_info.get(trace_id)
    return (
        None
        if trace_info_serialized is None
        else TraceInfo.FromString(trace_info_serialized)
    )


def get_resource_spans_list(
    trace_to_resource_spans: MutableMappingBytes, trace_id: str
) -> list[ResourceSpans] | None:
    resource_spans_list_serialized = trace_to_resource_spans.get(trace_id)
    return (
        None
        if resource_spans_list_serialized is None
        else ExportTraceServiceRequest.FromString(
            resource_spans_list_serialized
        ).resource_spans
    )
