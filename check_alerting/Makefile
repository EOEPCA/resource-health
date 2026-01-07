.PHONY : all gen-py start-trace-receiver start-notifier

gen-py:
	uv run python3 -m grpc_tools.protoc -I . --python_betterproto_out="proto" proto/trace_info.proto

start-trace-receiver:
	uv run python3 trace_receiver.py

start-notifier:
	uv run python3 notifier.py