FROM ubuntu:24.04

# Set environment variables to non-interactive (this will prevent some prompts)
ENV DEBIAN_FRONTEND=non-interactive

# Update package list and install basic Linux support tools
# Use apt-get instead of apt as that's the recommended one to use in scripts as it is more stable.
# See https://unix.stackexchange.com/a/731298
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    wget \
    git \
    ssh \
    gpg \
    python-is-python3 \
    python3 \
    python3-pip && \
    # Clean up after installation
    apt-get clean && apt-get remove pip && rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

COPY ./runner-image/run_script.sh /app/

## Replace with a (preinstalled) set of packages
COPY ./instrumentation/conftest.py /app/

RUN chmod +x /app/run_script.sh

ENTRYPOINT [ "/app/run_script.sh" ]