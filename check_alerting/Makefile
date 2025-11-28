.PHONY : all gen-py start-trace-receiver start-notifier

gen-py:
	cd .. && uv run python -m grpc_tools.protoc -I . --python_betterproto_out="proto" proto/trace_info.proto

start-trace-receiver:
	cd .. && uv run python3 trace_receiver.py

start-notifier:
	cd .. && uv run python3 notifier.py