from os import environ
from upath import UPath
exec(UPath(environ["RESOURCE_HEALTH_RUNNER_SCRIPT"]).read_text())
