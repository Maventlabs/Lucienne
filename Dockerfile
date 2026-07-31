# Lucienne Nightfall — Absolute Edition

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git build-essential \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy requirements
COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# FIX: Install fastmcp-slim[client] FIRST (provides mcp.client.auth)
# Then openhands-sdk (which needs it but doesn't declare it properly)
RUN uv pip install --system --no-cache-dir \
    "fastmcp-slim[client]" \
    openhands-sdk \
    openhands-tools \
    duckduckgo-search

# Copy app
COPY . /app
RUN mkdir -p /app/workspace /app/memory /app/soul

CMD ["python", "telegram_bridge.py"]
