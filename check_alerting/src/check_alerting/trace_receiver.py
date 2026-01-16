import binascii
import dbm
import logging
import threading
from concurrent import futures
from datetime import datetime, timezone

import grpc
from opentelemetry_betterproto.opentelemetry.proto.collector.trace.v1 import (
    ExportTracePartialSuccess,
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
    TraceServiceBase,
)
from opentelemetry_betterproto.opentelemetry.proto.common.v1 import InstrumentationScope
from opentelemetry_betterproto.opentelemetry.proto.resource.v1 import Resource
from opentelemetry_betterproto.opentelemetry.proto.trace.v1 import (
    ResourceSpans,
    ScopeSpans,
    Span,
    StatusStatusCode,
)

from check_alerting.common import (
    ERROR_TRACES_FILE,
    TRACE_INFO_STATUS_CODE_RECEIVING,
    TRACE_INFOS_FILE,
    get_int_env_var_or_default,
    get_resource_spans_list,
    get_str_env_var_or_default,
    get_trace_info,
)
from check_alerting.proto import TraceInfo, TraceInfoStatusCode

logger = logging.getLogger(name="trace_receiver")
# based on https://stackoverflow.com/a/76026506
logging.basicConfig(
    level=get_str_env_var_or_default("TRACE_RECEIVER_LOG_LEVEL", "INFO").upper()
)


def append_span(
    dict_resource_spans_list: list[ResourceSpans],
    resource: Resource,
    resource_schema_url: str,
    scope: InstrumentationScope,
    scope_schema_url: str,
    span: Span,
) -> None:
    if (
        len(dict_resource_spans_list) == 0
        or dict_resource_spans_list[-1].resource != resource
    ):
        dict_resource_spans_list.append(
            ResourceSpans(
                resource=resource, scope_spans=[], schema_url=resource_schema_url
            )
        )

    dict_scope_spans_list = dict_resource_spans_list[-1].scope_spans
    if len(dict_scope_spans_list) == 0 or dict_scope_spans_list[-1].scope != scope:
        dict_scope_spans_list.append(
            ScopeSpans(scope=scope, spans=[], schema_url=scope_schema_url)
        )

    dict_scope_spans_list[-1].spans.append(span)


thread_local = threading.local()


class TraceService:
    def export(
        self,
        export_trace_service_request: ExportTraceServiceRequest,
        context: grpc.RpcContext,
    ) -> ExportTraceServiceResponse:
        logger.debug("Got traces")
        if not hasattr(thread_local, "trace_to_resource_spans"):
            logger.debug("Open trace_to_resource_spans db connection for this thread")
            # TODO: should probably explicitly close the database connection before the program exits
            thread_local.trace_to_resource_spans = dbm.open(ERROR_TRACES_FILE, flag="c")
        trace_to_resource_spans: dbm._Database = thread_local.trace_to_resource_spans
        if not hasattr(thread_local, "trace_to_info"):
            logger.debug("Open trace_to_info db connection for this thread")
            thread_local.trace_to_info = dbm.open(TRACE_INFOS_FILE, flag="c")
        trace_to_info: dbm._Database = thread_local.trace_to_info

        error_trace_id_to_spans: dict[str, list[ResourceSpans]] = {}
        for resource_spans in export_trace_service_request.resource_spans:
            for scope_spans in resource_spans.scope_spans:
                for span in scope_spans.spans:
                    if span.status.code == StatusStatusCode.STATUS_CODE_ERROR:
                        # This is how telemetry API converts from trace id bytes to string
                        trace_id = binascii.b2a_hex(span.trace_id).decode("ascii")
                        append_span(
                            dict_resource_spans_list=error_trace_id_to_spans.setdefault(
                                trace_id, []
                            ),
                            resource=resource_spans.resource,
                            resource_schema_url=resource_spans.schema_url,
                            scope=scope_spans.scope,
                            scope_schema_url=scope_spans.schema_url,
                            span=span,
                        )
        if len(error_trace_id_to_spans) > 0:
            logger.info(f"Got {len(error_trace_id_to_spans)} error traces")
        for trace_id, resource_spans_list in error_trace_id_to_spans.items():
            trace_info = get_trace_info(trace_to_info, trace_id)

            trace_status: TraceInfoStatusCode = (
                TRACE_INFO_STATUS_CODE_RECEIVING
                if trace_info is None
                else trace_info.status
            )
            if trace_status != TraceInfoStatusCode.RECEIVING:
                logger.info(
                    f"Trace {trace_id} has status {trace_status.name}, so it is not saved"
                )
                continue
            db_resource_spans_list_serialized = trace_to_resource_spans.get(trace_id)
            db_resource_spans_list_or_none = get_resource_spans_list(
                trace_to_resource_spans, trace_id
            )
            db_resource_spans_list = (
                []
                if db_resource_spans_list_or_none is None
                else db_resource_spans_list_or_none
            )
            db_resource_spans_list.extend(resource_spans_list)

            # Want to do all the conversions first so that writing to the two
            # databases is with very short delay
            db_resource_spans_list_serialized = bytes(
                ExportTraceServiceRequest(resource_spans=db_resource_spans_list)
            )
            trace_info_serialized = bytes(
                TraceInfo(last_seen=datetime.now(timezone.utc), status=trace_status)
            )

            # Write trace info first so that all keys from self._trace_to_resource_spans
            # have a corresponding value in self._trace_to_info
            trace_to_info[trace_id] = trace_info_serialized
            trace_to_resource_spans[trace_id] = db_resource_spans_list_serialized
            logger.debug(
                f"Saved trace and info. There are {len(trace_to_info)} traces infos, and {len(trace_to_resource_spans)} traces saved"
            )

        return ExportTraceServiceResponse(ExportTracePartialSuccess(rejected_spans=0))


def main() -> None:
    logger.info("starting")
    max_workers = get_int_env_var_or_default("TRACE_RECEIVER_MAX_WORKERS", 20)
    address = get_str_env_var_or_default("TRACE_RECEIVER_ADDRESS", "[::]:50051")
    trace_service = TraceService()
    rpc_method_handlers = {
        "Export": grpc.unary_unary_rpc_method_handler(
            trace_service.export,
            request_deserializer=ExportTraceServiceRequest.FromString,
            response_serializer=ExportTraceServiceResponse.SerializeToString,
        )
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "opentelemetry.proto.collector.trace.v1.TraceService",
        rpc_method_handlers,
    )
    server = grpc.server(
        thread_pool=futures.ThreadPoolExecutor(max_workers=max_workers),
        handlers=[generic_handler],
    )
    server.add_insecure_port(address)
    logger.info("initialization done")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    main()
