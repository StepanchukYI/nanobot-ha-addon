ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system dependencies (Python already in base image)
RUN apk add --no-cache \
    nodejs \
    npm \
    git \
    curl \
    bash \
    jq \
    tzdata \
    py3-virtualenv

# Create virtual environment for clean dependency management
RUN python3 -m venv /opt/nanobot-venv

# Install nanobot + mcp-proxy
RUN /opt/nanobot-venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/nanobot-venv/bin/pip install --no-cache-dir "nanobot-ai>=0.1.4" "mcp-proxy>=0.3.0"

# Clone EWS MCP server (pip entry point is broken, must run from source)
RUN git clone --depth 1 https://github.com/azizmazrou/ews-mcp.git /opt/ews-mcp && \
    /opt/nanobot-venv/bin/pip install --no-cache-dir -r /opt/ews-mcp/requirements.txt

# Create wrapper script (official Dockerfile uses `python -m src.main`)
RUN printf '#!/bin/sh\ncd /opt/ews-mcp && exec /opt/nanobot-venv/bin/python -m src.main "$@"\n' \
    > /opt/nanobot-venv/bin/ews-mcp-server && chmod +x /opt/nanobot-venv/bin/ews-mcp-server

# Create persistent directories
RUN mkdir -p /data/nanobot /data/nanobot/workspace /data/nanobot/skills /data/.nanobot

# Copy addon scripts
COPY run.sh /
COPY generate_config.py /
COPY webui.py /
RUN chmod a+x /run.sh

# Healthcheck: check Web UI (always running), not gateway (slow to start)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:8080/ || exit 1

CMD [ "/run.sh" ]
