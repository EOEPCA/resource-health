.PHONY : start-collector send-trace

start-collector:
	./otelcol --config collector_config.yaml

send-trace:
	curl -H "Content-Type: application/json" -d @trace.json http://localhost:4318/v1/traces