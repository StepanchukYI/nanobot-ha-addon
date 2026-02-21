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

# Install nanobot
RUN /opt/nanobot-venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/nanobot-venv/bin/pip install --no-cache-dir "nanobot-ai>=0.1.4.post1"

# Create persistent directories
RUN mkdir -p /data/nanobot /data/nanobot/workspace /data/nanobot/skills /data/.nanobot

# Copy addon scripts
COPY run.sh /
COPY generate_config.py /
COPY webui.py /
RUN chmod a+x /run.sh

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf http://localhost:18790/health || exit 1

CMD [ "/run.sh" ]
