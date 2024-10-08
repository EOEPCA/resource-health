import sys
import pytest
from upath import UPath
from os import environ
from subprocess import check_call

if __name__ == "__main__":
    if "REQ_RUNNER_HEALTH" in environ:
        req_path = UPath(environ["REQ_RUNNER_HEALTH"])
        with open("requirements.txt", "w") as r:
            r.write(req_path.read_text())
        check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", "-r", "requirements.txt"])

    if "SCRIPT_RUNNER_HEALTH" in environ:
        sys.exit(pytest.main(["/app/run_script.py"]))
    else:
        sys.exit("Failure: Could not find SCRIPT_RUNNER_HEALTH.")

# For pytest.main()
exec(UPath(environ["SCRIPT_RUNNER_HEALTH"]).read_text(), globals())
