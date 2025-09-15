# Start from the llama.cpp light CUDA image
FROM ghcr.io/ggml-org/llama.cpp:light-cuda-b6458

ENV LD_LIBRARY_PATH=/app

RUN set -eux; \
    # Create a non-root user for security
    groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser && \
    # Update package lists and install dependencies
    apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    gnupg && \
    # Add the GitHub CLI repository and install gh
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
    apt-get update && \
    apt-get install -y gh && \
    # Clean up APT cache to reduce image size
    rm -rf /var/lib/apt/lists/*

# Switch to the newly created non-root user for security
USER appuser

WORKDIR /home/appuser

# Override the default entrypoint to be a bash shell
ENTRYPOINT ["/bin/bash"]