# Base stage with dependencies
FROM ubuntu:24.04 AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        libopenblas-dev \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Build stage: Compile llama.cpp
FROM base AS build

ARG COMMIT=master

WORKDIR /llama.cpp

RUN git clone --depth 1 --branch ${COMMIT} https://github.com/ggml-org/llama.cpp . && \
    mkdir build && cd build && \
    cmake .. \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLAMA_BLAS=ON \
        -DLLAMA_BLAS_VENDOR=OpenBLAS && \
    cmake --build . --config Release --parallel $(nproc)

# Light target: Basic main and quantize
FROM base AS light

COPY --from=build /llama.cpp/build/bin/main /bin/main
COPY --from=build /llama.cpp/build/bin/quantize /bin/quantize

ENTRYPOINT ["/bin/main"]

# Server target: Adds server executable
FROM light AS server

COPY --from=build /llama.cpp/build/bin/server /bin/server

ENTRYPOINT ["/bin/server"]

# Full target: All binaries
FROM base AS full

COPY --from=build /llama.cpp/build/bin/* /bin/

ENTRYPOINT ["/bin/main"]