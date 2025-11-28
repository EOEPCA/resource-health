import binascii
from logging import warning
import logging
import grpc
from opentelemetry_betterproto.opentelemetry.proto.collector.trace.v1 import (
    TraceServiceBase,
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
    ExportTracePartialSuccess,
)
from opentelemetry_betterproto.opentelemetry.proto.trace.v1 import StatusStatusCode
from concurrent import futures

# class TraceService(TraceServiceBase):
#     async def export(
#         self, export_trace_service_request: ExportTraceServiceRequest
#     ) -> ExportTraceServiceResponse:
#         warning("GOT A REQUEST")
#         return ExportTraceServiceResponse(ExportTracePartialSuccess(rejected_spans=0))


# This doesn't make sense. My guess is that version mismatch causes this
# I use TraceServiceBase as a base class according to https://grpc.io/docs/languages/python/basics
# But the actual method needs one more argument (I think it's "context" like in https://github.com/grpc/grpc/blob/v1.76.0/examples/python/route_guide/route_guide_pb2_grpc.py#L40)
# Also nothing awaits the method, so it cannot be async
class TraceService:
    def export(
        self,
        export_trace_service_request: ExportTraceServiceRequest,
        context: grpc.RpcContext,
    ) -> ExportTraceServiceResponse:
        error_traces: set[str] = set()
        for resource_spans in export_trace_service_request.resource_spans:
            for scope_spans in resource_spans.scope_spans:
                for span in scope_spans.spans:
                    if span.status.code == StatusStatusCode.Error:
                        # This is how telemetry API converts from trace id bytes to string
                        trace_id = binascii.b2a_hex(span.trace_id).decode("ascii")
                        error_traces.add(trace_id)
        print(f"Error traces {error_traces}")
        return ExportTraceServiceResponse(ExportTracePartialSuccess(rejected_spans=0))


def serve() -> None:
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
        thread_pool=futures.ThreadPoolExecutor(max_workers=10),
        handlers=[generic_handler],
    )
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
