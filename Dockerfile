# Production Dockerfile for KuzuMemPy MCP Server
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash cognitive_fabric

# Set working directory
WORKDIR /app

# Install uv for faster package management
RUN pip install uv

# Copy project files
COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/

# Install dependencies using uv
RUN uv pip install --system -e .

# Create data directory
RUN mkdir -p /app/data && chown -R cognitive_fabric:cognitive_fabric /app

# Switch to non-root user
USER cognitive_fabric

# Set data directory as volume
VOLUME ["/app/data"]

# Default environment variables
ENV COGNITIVE_FABRIC_DB_PATH=/app/data/cognitive_fabric.db \
    COGNITIVE_FABRIC_LOG_LEVEL=INFO \
    COGNITIVE_FABRIC_LOG_FORMAT=json

# Entry point for the MCP server
CMD ["python", "-m", "cognitive_fabric.main"]
