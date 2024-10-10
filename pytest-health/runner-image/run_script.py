import upath
import os

if __name__ == "__main__":
    import sys
    from subprocess import check_call
    if "RESOURCE_HEALTH_RUNNER_REQUIREMENTS" in os.environ:
        req_path = upath.UPath(os.environ["RESOURCE_HEALTH_RUNNER_REQUIREMENTS"])
        with open("requirements.txt", "w") as r:
            r.write(req_path.read_text())
        check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    if "RESOURCE_HEALTH_RUNNER_SCRIPT" in os.environ:
        from opentelemetry.instrumentation.auto_instrumentation import run
        # run() starts opentelemetry-instrument and uses arguments in sys.argv
        # Change name of executable to avoid confusion in error messages
        sys.argv[0] = "opentelemetry-instrument"
        sys.exit(run())
    else:
        sys.exit("Failure: Could not find RESOURCE_HEALTH_RUNNER_SCRIPT.")

# Execute function definitions for pytest
exec(upath.UPath(os.environ["RESOURCE_HEALTH_RUNNER_SCRIPT"]).read_text(), globals())
