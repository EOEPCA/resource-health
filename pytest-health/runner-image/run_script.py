from upath import UPath
from os import environ
from subprocess import check_call
from sys import executable
from pytest import main

if "REQ_RUNNER_HEALTH" in environ:
    req_path = UPath(environ["REQ_RUNNER_HEALTH"])
    with open("requirements.txt", "w") as r:
        r.write(req_path.read_text())
    check_call([executable, "-m", "pip", "install", "--break-system-packages", "-r", "requirements.txt"])

if "SCRIPT_RUNNER_HEALTH" in environ:
    script_path = UPath(environ["SCRIPT_RUNNER_HEALTH"])
    script = script_path.read_text()
    with open("script.py", "w") as s:
        s.write(script)
    main(["script.py"])
else:
    print("Failure: Could not find SCRIPT_RUNNER_HEALTH.")
