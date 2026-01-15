.PHONY : all gen-py start-trace-receiver start-notifier

gen-py:
	uv run python3 -m grpc_tools.protoc -I . --python_betterproto_out="src/check_alerting/proto" src/check_alerting/proto/trace_info.proto

start-trace-receiver:
	uv run python3 src/check_alerting/trace_receiver.py

start-notifier:
	uv run python3 src/check_alerting/notifier.py