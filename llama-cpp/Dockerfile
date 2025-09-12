# Use Ubuntu 22.04 for a consistent build environment
ARG UBUNTU_VERSION=22.04

# =================================
# Builder Stage
# Compiles the llama.cpp source code
# =================================
FROM ubuntu:$UBUNTU_VERSION AS build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential git cmake libcurl4-openssl-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all source code from your repository into the container
COPY . .

# Compile llama.cpp for CPU with generic settings for broad compatibility
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_NATIVE=OFF -DLLAMA_BUILD_TESTS=OFF && \
    cmake --build build --config Release -j $(nproc)

# Consolidate all build artifacts into a single directory for easier copying
RUN mkdir -p /app/artifacts \
    && cp build/bin/* /app/artifacts \
    && cp *.py /app/artifacts \
    && cp -r gguf-py /app/artifacts \
    && cp -r requirements /app/artifacts \
    && cp requirements.txt /app/artifacts \
    # NOTE: This assumes you have a 'tools.sh' script in your repo root.
    && if [ -f "tools.sh" ]; then cp tools.sh /app/artifacts/tools.sh; fi

# =================================
# Base Stage
# Creates a minimal runtime environment
# =================================
FROM ubuntu:$UBUNTU_VERSION AS base

# Install only essential runtime libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 curl && \
    # Clean up to reduce final image size
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

# =================================
# Final Image: full
# Includes all tools and Python dependencies
# =================================
FROM base AS full

WORKDIR /app
COPY --from=build /app/artifacts /app

# Install Python and dependencies from requirements.txt
RUN apt-get update && \
    apt-get install -y --no-install-recommends git python3 python3-pip && \
    pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/app/tools.sh"]

# =================================
# Final Image: light
# Minimal image with only the CLI tool
# =================================
FROM base AS light

# Copy only the 'llama-cli' binary from the builder stage
COPY --from=build /app/artifacts/llama-cli /usr/local/bin/
ENTRYPOINT ["llama-cli"]

# =================================
# Final Image: server
# Minimal image with only the web server
# =================================
FROM base AS server

ENV HOST=0.0.0.0
ENV PORT=8080

# Copy only the 'llama-server' binary from the builder stage
COPY --from=build /app/artifacts/llama-server /usr/local/bin/

HEALTHCHECK CMD [ "curl", "-f", "http://localhost:8080/health" ]
ENTRYPOINT [ "llama-server" ]