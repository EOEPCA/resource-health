from check_backends.k8s_backend.template_utils import *

class SimplePingArguments(BaseModel):
    endpoint : str = Field(json_schema_extra={'format':'textarea'})
    expected_status_code : int = Field(ge=100, lt=600, default=200)

# def simple_ping_annotations(self, template_args : SimplePingArguments) -> dict[str, Any]:
#     return {}

def simple_ping_containers(template_args : SimplePingArguments) -> list[Container]:
    return [
        container(
            image=DEFAULT_CONTAINER_IMAGE,
            env={
                "RESOURCE_HEALTH_RUNNER_SCRIPT" : "data:text/plain;base64,ZnJvbSBvcyBpbXBvcnQgZW52aXJvbgppbXBvcnQgcmVxdWVzdHMKCkdFTkVSSUNfRU5EUE9JTlQ6IHN0ciA9IGVudmlyb25bIkdFTkVSSUNfRU5EUE9JTlQiXQpFWFBFQ1RFRF9TVEFUVVNfQ09ERTogaW50ID0gaW50KGVudmlyb25bIkVYUEVDVEVEX1NUQVRVU19DT0RFIl0pCgoKZGVmIHRlc3RfcGluZygpIC0+IE5vbmU6CiAgICByZXNwb25zZSA9IHJlcXVlc3RzLmdldCgKICAgICAgICBHRU5FUklDX0VORFBPSU5ULAogICAgKQogICAgYXNzZXJ0IHJlc3BvbnNlLnN0YXR1c19jb2RlID09IEVYUEVDVEVEX1NUQVRVU19DT0RFCg==",
                "GENERIC_ENDPOINT": template_args.endpoint,
                "EXPECTED_STATUS_CODE" : str(template_args.expected_status_code),
            }
        )
    ]

SimplePing = cronjob_template(
    template_id = "simple_ping",
    argument_type = SimplePingArguments,
    label = "Simple ping template",
    description = "Simple template with preset script for pinging single endpoint.",
    # annotations = simple_ping_annotations,
    containers = simple_ping_containers,
)
